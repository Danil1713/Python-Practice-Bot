from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageText,
)

from app.bot import error_handler


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "message"),
    [
        (
            AnswerCallbackQuery(
                callback_query_id="callback-id",
            ),
            (
                "Bad Request: query is too old and response "
                "timeout expired or query ID is invalid"
            ),
        ),
        (
            EditMessageText(
                chat_id=1,
                message_id=2,
                text="Same text",
            ),
            "Bad Request: message is not modified",
        ),
    ],
)
async def test_expected_telegram_errors_are_not_logged_as_unhandled(
    monkeypatch,
    method,
    message,
):
    logger = Mock()
    monkeypatch.setattr(
        error_handler,
        "logger",
        logger,
    )

    exception = TelegramBadRequest(
        method=method,
        message=message,
    )

    event = SimpleNamespace(
        update=SimpleNamespace(update_id=42),
        exception=exception,
    )

    handled = await error_handler.global_error_handler(event)

    assert handled is True

    logger.warning.assert_called_once_with(
        "Ignored expected Telegram error update_id=%s error=%s",
        42,
        message,
    )

    logger.error.assert_not_called()


@pytest.mark.asyncio
async def test_unexpected_error_is_logged_with_traceback(
    monkeypatch,
):
    logger = Mock()
    monkeypatch.setattr(
        error_handler,
        "logger",
        logger,
    )

    exception = RuntimeError("Unexpected failure")

    event = SimpleNamespace(
        update=SimpleNamespace(update_id=43),
        exception=exception,
    )

    handled = await error_handler.global_error_handler(event)

    assert handled is True

    logger.warning.assert_not_called()
    logger.error.assert_called_once()
