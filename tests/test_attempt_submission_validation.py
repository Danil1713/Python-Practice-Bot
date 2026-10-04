from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.handlers import attempts_submission


@pytest.mark.asyncio
async def test_wrong_solution_extension_explains_retry(
    monkeypatch: pytest.MonkeyPatch,
):
    check_current_course = AsyncMock(return_value=True)

    monkeypatch.setattr(
        attempts_submission,
        "check_current_course",
        check_current_course,
    )

    state = AsyncMock()

    state.get_data.return_value = {
        "project_id": 123,
        "course_slug": "demo",
    }

    message = SimpleNamespace(
        from_user=SimpleNamespace(id=1),
        document=SimpleNamespace(
            file_name="solution.txt",
            file_size=100,
        ),
        answer=AsyncMock(),
    )

    bot = AsyncMock()

    await attempts_submission.solution_file_handler(
        message,
        state,
        bot,
    )

    bot.download.assert_not_awaited()
    state.clear.assert_not_awaited()

    answer = message.answer.await_args

    assert "расширением" in answer.kwargs["text"]
    assert "отправь" in answer.kwargs["text"].lower()
    assert "Бот продолжает ждать файл" in (answer.kwargs["text"])


@pytest.mark.asyncio
async def test_non_file_message_explains_retry(
    monkeypatch: pytest.MonkeyPatch,
):
    check_current_course = AsyncMock(return_value=True)

    monkeypatch.setattr(
        attempts_submission,
        "check_current_course",
        check_current_course,
    )

    state = AsyncMock()

    state.get_data.return_value = {
        "project_id": 123,
        "course_slug": "demo",
    }

    message = SimpleNamespace(
        from_user=SimpleNamespace(id=1),
        answer=AsyncMock(),
    )

    await attempts_submission.wrong_solution_message_handler(
        message,
        state,
    )

    state.clear.assert_not_awaited()

    answer = message.answer.await_args

    assert "именно файл" in answer.kwargs["text"]
    assert "Бот продолжает ждать файл" in (answer.kwargs["text"])
