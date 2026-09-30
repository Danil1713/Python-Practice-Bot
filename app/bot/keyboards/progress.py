from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.bot.callbacks import (
    build_callback_data,
)


def get_progress_keyboard(
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 Проекты",
                    callback_data=build_callback_data(
                        "menu",
                        "projects",
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
