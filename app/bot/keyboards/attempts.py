from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.bot.callbacks import (
    build_callback_data,
)
from app.services.attempt_service import (
    AttemptListItem,
)

ATTEMPT_ICONS = {
    "pending": "⏳",
    "checking": "⏳",
    "failed": "❌",
    "passed": "✅",
    "review": "🟠",
    "error": "⚠️",
}


def get_cancel_submission_keyboard(
    project_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=build_callback_data(
                        "attempt",
                        "cancel",
                        project_id,
                    ),
                )
            ]
        ]
    )


def get_attempts_keyboard(
    attempts: list[AttemptListItem],
    project_id: int,
) -> InlineKeyboardMarkup:
    buttons = []

    for attempt in attempts:
        icon = ATTEMPT_ICONS.get(
            attempt.status,
            "❔",
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(f"{icon} Попытка №{attempt.number}"),
                    callback_data=build_callback_data(
                        "attempt",
                        "open",
                        attempt.id,
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=build_callback_data(
                    "project",
                    "open",
                    project_id,
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_attempt_detail_keyboard(
    attempt_id: int,
    project_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Мой код",
                    callback_data=build_callback_data(
                        "attempt",
                        "code",
                        attempt_id,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🤖 Результат проверки",
                    callback_data=build_callback_data(
                        "attempt",
                        "feedback",
                        attempt_id,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=build_callback_data(
                        "project",
                        "attempts",
                        project_id,
                    ),
                )
            ],
        ]
    )


def get_ai_review_consent_keyboard(
    project_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Согласен",
                    callback_data=build_callback_data(
                        "attempt",
                        "ai-consent",
                        project_id,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data=build_callback_data(
                        "attempt",
                        "cancel",
                        project_id,
                    ),
                )
            ],
        ]
    )
