from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.database.models.course import Course


def get_courses_keyboard(
    courses: list[Course],
) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=course.title,
                callback_data=f"course:{course.slug}",
            )
        ]
        for course in courses
    ]

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )