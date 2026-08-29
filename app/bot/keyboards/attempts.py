from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.services.attempt_service import (
    AttemptListItem,
)


ATTEMPT_ICONS = {
    "pending": "⏳",
    "checking": "⏳",
    "failed": "❌",
    "passed": "✅",
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
                    callback_data=(
                        f"attempt:cancel:{project_id}"
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
                    text=(
                        f"{icon} Попытка "
                        f"№{attempt.number}"
                    ),
                    callback_data=(
                        f"attempt:open:{attempt.id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=(
                    f"project:open:{project_id}"
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def get_attempt_detail_keyboard(
    attempt_id: int,
    project_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Мой код",
                    callback_data=(
                        f"attempt:code:{attempt_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🤖 Результат проверки",
                    callback_data=(
                        f"attempt:feedback:{attempt_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=(
                        f"project:attempts:"
                        f"{project_id}"
                    ),
                )
            ],
        ]
    )