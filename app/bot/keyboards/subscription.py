from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_app_timezone

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def get_subscription_keyboard(
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=(
                        f"nav:menu:{course_slug}"
                    ),
                )
            ]
        ]
    )

def format_subscription_datetime(
    value: datetime,
) -> str:
    timezone = ZoneInfo(
        get_app_timezone()
    )

    local_value = value.astimezone(
        timezone
    )

    return local_value.strftime(
        "%d.%m.%Y %H:%M"
    )