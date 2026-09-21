from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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
        icon = (
            "💡"
            if hint.is_published
            else "🔒"
        )

        if hint.telegram_url is not None:
            button = InlineKeyboardButton(
                text=(
                    f"{icon} Подсказка "
                    f"{hint.number}"
                ),
                url=hint.telegram_url,
            )

        else:
            button = InlineKeyboardButton(
                text=(
                    f"{icon} Подсказка "
                    f"{hint.number}"
                ),
                callback_data=(
                    f"hint:open:{hint.id}"
                ),
            )

        buttons.append(
            [button]
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