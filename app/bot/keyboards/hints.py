from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.bot.callbacks import (
    build_callback_data,
)
from app.services.hint_service import (
    HintListItem,
)


def get_hints_keyboard(
    hints: list[HintListItem],
    project_id: int,
) -> InlineKeyboardMarkup:
    buttons = []

    for hint in hints:
        icon = "💡" if hint.is_published else "🔒"

        if hint.telegram_url is not None:
            button = InlineKeyboardButton(
                text=f"{icon} Подсказка {hint.number}",
                url=hint.telegram_url,
            )
        else:
            button = InlineKeyboardButton(
                text=f"{icon} Подсказка {hint.number}",
                callback_data=build_callback_data(
                    "hint",
                    "open",
                    hint.id,
                ),
            )

        buttons.append([button])

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


def get_hint_open_keyboard(
    telegram_url: str,
    project_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💡 Открыть подсказку",
                    url=telegram_url,
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=build_callback_data(
                        "project",
                        "hints",
                        project_id,
                    ),
                )
            ],
        ]
    )
