from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.bot.callbacks import (
    build_callback_data,
)
from app.services.project_service import (
    ProjectListItem,
)

STATUS_ICONS = {
    "locked": "🔒",
    "available": "🟡",
    "pending": "⏳",
    "completed": "✅",
}

PROJECTS_PER_PAGE = 8


def get_projects_keyboard(
    projects: list[ProjectListItem],
    course_slug: str,
    page: int = 0,
) -> InlineKeyboardMarkup:
    total_projects = len(projects)

    total_pages = max(
        1,
        (
            total_projects
            + PROJECTS_PER_PAGE
            - 1
        )
        // PROJECTS_PER_PAGE,
    )

    page = max(
        0,
        min(
            page,
            total_pages - 1,
        ),
    )

    start = (
        page * PROJECTS_PER_PAGE
    )

    end = (
        start + PROJECTS_PER_PAGE
    )

    page_projects = projects[
        start:end
    ]

    buttons = []

    for project in page_projects:
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
                    callback_data=build_callback_data(
                        "project",
                        "open",
                        project.id,
                    ),
                )
            ]
        )

    if total_pages > 1:
        navigation = []

        if page > 0:
            navigation.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=build_callback_data(
                        "projects",
                        "page",
                        page - 1,
                        course_slug,
                    ),
                )
            )

        navigation.append(
            InlineKeyboardButton(
                text=(
                    f"{page + 1} / "
                    f"{total_pages}"
                ),
                callback_data=build_callback_data(
                    "projects",
                    "page",
                    page,
                    course_slug,
                ),
            )
        )

        if page < total_pages - 1:
            navigation.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=build_callback_data(
                        "projects",
                        "page",
                        page + 1,
                        course_slug,
                    ),
                )
            )

        buttons.append(
            navigation
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=build_callback_data(
                    "nav",
                    "menu",
                    course_slug,
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=build_callback_data(
                    "nav",
                    "menu",
                    course_slug,
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
    task_url: str | None = None,
) -> InlineKeyboardMarkup:
    if task_url is not None:
        task_button = InlineKeyboardButton(
            text="📖 Открыть задание",
            url=task_url,
        )
    else:
        task_button = InlineKeyboardButton(
            text="📖 Открыть задание",
            callback_data=build_callback_data(
                "project",
                "task",
                project_id,
            ),
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                task_button
            ],
            [
                InlineKeyboardButton(
                    text="📤 Отправить решение",
                    callback_data=build_callback_data(
                        "project",
                        "submit",
                        project_id,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="💡 Подсказки",
                    callback_data=build_callback_data(
                        "project",
                        "hints",
                        project_id,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧾 Мои попытки",
                    callback_data=build_callback_data(
                        "project",
                        "attempts",
                        project_id,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=build_callback_data(
                        "menu",
                        "projects",
                        course_slug,
                    ),
                )
            ],
        ]
    )