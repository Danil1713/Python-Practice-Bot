from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import ai_service
from app.services.ai_service import (
    CodeReviewResult,
    RequirementReview,
)


def make_review_result() -> CodeReviewResult:
    return CodeReviewResult(
        verdict="passed",
        requirements_complete=True,
        criteria=[
            RequirementReview(
                requirement="Использовать цикл",
                status="passed",
                explanation="Цикл присутствует в коде.",
            )
        ],
        summary="Все требования выполнены.",
        strengths=["Корректная структура."],
        problems=[],
        recommendations=[],
    )


def make_response():
    return SimpleNamespace(
        output_parsed=make_review_result(),
        usage=SimpleNamespace(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        ),
    )


def configure_ai(
    monkeypatch,
    *,
    max_attempts: int = 1,
) -> None:
    monkeypatch.setattr(
        ai_service,
        "get_ai_model",
        lambda: "gpt-5.6-terra",
    )

    monkeypatch.setattr(
        ai_service,
        "get_ai_reasoning_effort",
        lambda: "low",
    )

    monkeypatch.setattr(
        ai_service,
        "get_ai_max_output_tokens",
        lambda: 3000,
    )

    monkeypatch.setattr(
        ai_service,
        "get_ai_timeout_seconds",
        lambda: 1,
    )

    monkeypatch.setattr(
        ai_service,
        "get_ai_max_attempts",
        lambda: max_attempts,
    )

    monkeypatch.setattr(
        ai_service,
        "get_ai_retry_base_delay_seconds",
        lambda: 0.25,
    )


@pytest.mark.asyncio
async def test_openai_review_uses_responses_structured_output(
    monkeypatch,
):
    configure_ai(monkeypatch)

    parse = AsyncMock(
        return_value=make_response(),
    )

    client = SimpleNamespace(
        responses=SimpleNamespace(
            parse=parse,
        )
    )

    monkeypatch.setattr(
        ai_service,
        "get_ai_client",
        lambda: client,
    )

    result = await ai_service.review_python_code(
        project_title="Циклы",
        requirements="Использовать цикл",
        source_code="for number in range(3):\n    print(number)",
    )

    assert result.verdict == "passed"
    assert result.requirements_complete is True

    parse.assert_awaited_once()

    request = parse.await_args.kwargs

    assert request["model"] == "gpt-5.6-terra"
    assert request["instructions"] == (ai_service.SYSTEM_INSTRUCTION)
    assert request["text_format"] is CodeReviewResult
    assert request["reasoning"] == {
        "effort": "low",
    }
    assert request["max_output_tokens"] == 3000
    assert request["store"] is False

    assert "Проект: Циклы" in request["input"]
    assert "Использовать цикл" in request["input"]
    assert "<student_code>" in request["input"]
    assert "for number in range(3)" in request["input"]


@pytest.mark.asyncio
async def test_openai_timeout_is_retried(
    monkeypatch,
):
    configure_ai(
        monkeypatch,
        max_attempts=2,
    )

    parse = AsyncMock(
        side_effect=[
            TimeoutError("OpenAI timeout"),
            make_response(),
        ],
    )

    client = SimpleNamespace(
        responses=SimpleNamespace(
            parse=parse,
        )
    )

    sleep = AsyncMock()

    monkeypatch.setattr(
        ai_service,
        "get_ai_client",
        lambda: client,
    )

    monkeypatch.setattr(
        ai_service.asyncio,
        "sleep",
        sleep,
    )

    response = await ai_service.request_review(
        "Test prompt",
    )

    assert response.output_parsed.verdict == "passed"
    assert parse.await_count == 2

    sleep.assert_awaited_once_with(0.25)


@pytest.mark.asyncio
async def test_non_retriable_openai_error_is_not_retried(
    monkeypatch,
):
    configure_ai(
        monkeypatch,
        max_attempts=3,
    )

    parse = AsyncMock(
        side_effect=ValueError("Invalid structured response"),
    )

    client = SimpleNamespace(
        responses=SimpleNamespace(
            parse=parse,
        )
    )

    sleep = AsyncMock()

    monkeypatch.setattr(
        ai_service,
        "get_ai_client",
        lambda: client,
    )

    monkeypatch.setattr(
        ai_service.asyncio,
        "sleep",
        sleep,
    )

    with pytest.raises(
        ValueError,
        match="Invalid structured response",
    ):
        await ai_service.request_review(
            "Test prompt",
        )

    assert parse.await_count == 1
    sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_openai_client_is_closed_and_cleared(
    monkeypatch,
):
    client = SimpleNamespace(
        close=AsyncMock(),
    )

    monkeypatch.setattr(
        ai_service,
        "_client",
        client,
    )

    await ai_service.close_ai_client()

    client.close.assert_awaited_once_with()
    assert ai_service._client is None
