from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.bot.callbacks import (
    build_callback_data,
)


def get_xp_keyboard(
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Прогресс",
                    callback_data=build_callback_data(
                        "menu",
                        "progress",
                        course_slug,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=build_callback_data(
                        "nav",
                        "menu",
                        course_slug,
                    ),
                )
            ],
        ]
    )
