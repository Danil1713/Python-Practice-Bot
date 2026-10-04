import pytest

from app.config import (
    get_ai_max_output_tokens,
    get_ai_model,
    get_ai_reasoning_effort,
)


def test_openai_model_is_used_by_default(
    monkeypatch,
):
    monkeypatch.delenv(
        "AI_MODEL",
        raising=False,
    )

    assert get_ai_model() == "gpt-5.6-terra"


def test_ai_reasoning_effort_is_low_by_default(
    monkeypatch,
):
    monkeypatch.delenv(
        "AI_REASONING_EFFORT",
        raising=False,
    )

    assert get_ai_reasoning_effort() == "low"


def test_invalid_ai_reasoning_effort_is_rejected(
    monkeypatch,
):
    monkeypatch.setenv(
        "AI_REASONING_EFFORT",
        "invalid",
    )

    with pytest.raises(
        RuntimeError,
        match="AI_REASONING_EFFORT",
    ):
        get_ai_reasoning_effort()


def test_ai_max_output_tokens_must_be_positive(
    monkeypatch,
):
    monkeypatch.setenv(
        "AI_MAX_OUTPUT_TOKENS",
        "0",
    )

    with pytest.raises(
        RuntimeError,
        match="AI_MAX_OUTPUT_TOKENS",
    ):
        get_ai_max_output_tokens()
