from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def get_dismiss_notification_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Скрыть",
                    callback_data="notification:dismiss",
                )
            ]
        ]
    )
