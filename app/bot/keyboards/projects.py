from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.services.project_service import (
    ProjectListItem,
)


STATUS_ICONS = {
    "locked": "🔒",
    "available": "🟡",
    "completed": "✅",
}


def get_projects_keyboard(
    projects: list[ProjectListItem],
    course_slug: str,
) -> InlineKeyboardMarkup:
    buttons = []

    for project in projects:
        icon = STATUS_ICONS[
            project.status
        ]

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{icon} Project "
                        f"{project.number} — "
                        f"{project.title}"
                    ),
                    callback_data=(
                        f"project:open:"
                        f"{project.id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=(
                    f"nav:menu:{course_slug}"
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def get_project_card_keyboard(
    project_id: int,
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 Открыть задание",
                    callback_data=(
                        f"project:task:{project_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📤 Отправить решение",
                    callback_data=(
                        f"project:submit:{project_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="💡 Подсказки",
                    callback_data=(
                        f"project:hints:{project_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧾 Мои попытки",
                    callback_data=(
                        f"project:attempts:{project_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=(
                        f"menu:projects:"
                        f"{course_slug}"
                    ),
                )
            ],
        ]
    )