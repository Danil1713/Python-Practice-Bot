from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.bot.callbacks import (
    build_callback_data,
)
from app.config import get_admin_username, get_app_timezone


def get_subscription_keyboard(
    course_slug: str,
    *,
    can_pay: bool,
    can_open_channel: bool = False,
    stars_price: int | None = None,
    admin_username: str | None = None,
) -> InlineKeyboardMarkup:
    rows = []

    if can_open_channel:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📢 Доступ к каналу",
                    callback_data=build_callback_data(
                        "subscription",
                        "channel",
                        course_slug,
                    ),
                )
            ]
        )

    if can_pay and stars_price is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text=(f"⭐ Купить за {stars_price} Stars"),
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
                    url=(f"https://t.me/{admin_username}"),
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

    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_subscription_datetime(
    value: datetime,
) -> str:
    timezone = ZoneInfo(get_app_timezone())

    local_value = value.astimezone(timezone)

    return local_value.strftime("%d.%m.%Y %H:%M")


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

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_channel_join_keyboard(
    *,
    invite_link: str,
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Отправить заявку",
                    url=invite_link,
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к подписке",
                    callback_data=build_callback_data(
                        "menu",
                        "subscription",
                        course_slug,
                    ),
                )
            ],
        ]
    )
