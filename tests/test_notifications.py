from unittest.mock import AsyncMock

import pytest

from app.bot.handlers.notifications import (
    dismiss_notification_handler,
)
from app.bot.keyboards.notifications import (
    get_dismiss_notification_keyboard,
)


def test_dismiss_notification_keyboard():
    keyboard = get_dismiss_notification_keyboard()

    button = keyboard.inline_keyboard[0][0]

    assert button.text == "Скрыть"
    assert button.callback_data == "notification:dismiss"


@pytest.mark.asyncio
async def test_dismiss_notification_deletes_message():
    callback = AsyncMock()

    await dismiss_notification_handler(callback)

    callback.message.delete.assert_awaited_once_with()
    callback.answer.assert_awaited_once_with()
