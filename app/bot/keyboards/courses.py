from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.bot.callbacks import build_callback_data
from app.database.models.course import Course


def get_courses_keyboard(
    courses: list[Course],
) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=course.title,
                callback_data=build_callback_data(
                    "course",
                    course.slug,
                ),
            )
        ]
        for course in courses
    ]

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )