from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def get_progress_keyboard(
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 Проекты",
                    callback_data=(
                        f"menu:projects:{course_slug}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=(
                        f"nav:menu:{course_slug}"
                    ),
                )
            ],
        ]
    )