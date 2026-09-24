from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_app_timezone, get_admin_username

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from app.bot.callbacks import (
    build_callback_data,
)

def get_subscription_keyboard(
    course_slug: str,
    *,
    can_pay: bool,
    stars_price: int | None = None,
    admin_username: str | None = None,
) -> InlineKeyboardMarkup:
    rows = []

    if can_pay and stars_price is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"⭐ Купить за "
                        f"{stars_price} Stars"
                    ),
                    callback_data=build_callback_data(
                        "payment",
                        "stars",
                        course_slug,
                    ),
                )
            ]
        )

    if admin_username:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💬 Купить вручную",
                    url=(
                        f"https://t.me/"
                        f"{admin_username}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🆘 Помощь с оплатой",
                callback_data=build_callback_data(
                    "payment",
                    "support",
                    course_slug,
                ),
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=build_callback_data(
                    "nav",
                    "menu",
                    course_slug,
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
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

def get_stars_invoice_keyboard(
    payment_id: int,
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ Оплатить",
                    pay=True,
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=build_callback_data(
                        "payment",
                        "cancel",
                        payment_id,
                        course_slug,
                    ),
                )
            ],
        ]
    )

def get_payment_support_keyboard(
    course_slug: str | None = None,
) -> InlineKeyboardMarkup:
    admin_username = get_admin_username()

    rows = [
        [
            InlineKeyboardButton(
                text="💬 Написать администратору",
                url=f"https://t.me/{admin_username}",
            )
        ]
    ]

    if course_slug is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=build_callback_data(
                        "menu",
                        "subscription",
                        course_slug,
                    ),
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )