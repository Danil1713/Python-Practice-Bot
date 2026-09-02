from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def get_xp_keyboard(
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Прогресс",
                    callback_data=(
                        f"menu:progress:{course_slug}"
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