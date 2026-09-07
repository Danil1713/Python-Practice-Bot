from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def get_admin_menu_keyboard(
    course_slug: str,
    requires_subscription: bool,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="📅 Расписание",
                callback_data=(
                    f"admin:schedule:{course_slug}"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                text="➕ Добавить публикацию",
                callback_data=(
                    f"admin:add:start:{course_slug}"
                ),
            )
        ],
    ]

    if requires_subscription:
        rows.append(
            [
                InlineKeyboardButton(
                    text="👤 Подписки",
                    callback_data=(
                        f"admin:subscriptions:"
                        f"{course_slug}"
                    ),
                )
            ]
        )

    rows.append(
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
        inline_keyboard=rows
    )

def get_schedule_keyboard(
    course_slug: str,
    posts: list,
) -> InlineKeyboardMarkup:
    rows = []

    status_icons = {
        "scheduled": "🕒",
        "failed": "⚠️",
    }

    type_icons = {
        "regular": "📝",
        "project": "🚀",
        "hint": "💡",
    }

    for post in posts:
        status_icon = status_icons.get(
            post.status,
            "❔",
        )

        type_icon = type_icons.get(
            post.post_type,
            "📝",
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{status_icon} "
                        f"{type_icon} "
                        f"#{post.id}"
                    ),
                    callback_data=(
                        f"admin:post:{post.id}:"
                        f"{course_slug}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="➕ Добавить",
                callback_data=(
                    f"admin:add:start:{course_slug}"
                ),
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=(
                    f"admin:menu:{course_slug}"
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )

def get_scheduled_post_keyboard(
    post_id: int,
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Опубликовать сейчас",
                    callback_data=(
                        f"admin:publish:{post_id}:"
                        f"{course_slug}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🕒 Перенести",
                    callback_data=(
                        f"admin:reschedule:{post_id}:"
                        f"{course_slug}"
                    ),
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=(
                        f"admin:cancel:{post_id}:"
                        f"{course_slug}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=(
                        f"admin:schedule:{course_slug}"
                    ),
                )
            ],
        ]
    )

def get_admin_input_cancel_keyboard(
    post_id: int,
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=(
                        f"admin:post:{post_id}:"
                        f"{course_slug}"
                    ),
                )
            ]
        ]
    )

def get_post_type_keyboard(
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Обычный пост",
                    callback_data=(
                        f"admin:add:type:regular:"
                        f"{course_slug}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚀 Project",
                    callback_data=(
                        f"admin:add:type:project:"
                        f"{course_slug}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="💡 Hint",
                    callback_data=(
                        f"admin:add:type:hint:"
                        f"{course_slug}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=(
                        f"admin:menu:{course_slug}"
                    ),
                )
            ],
        ]
    )

def get_project_selection_keyboard(
    course_slug: str,
    projects: list,
) -> InlineKeyboardMarkup:
    rows = []

    for project in projects:
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"Project {project.number} — "
                        f"{project.title}"
                    ),
                    callback_data=(
                        f"admin:add:project:"
                        f"{project.id}:"
                        f"{course_slug}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=(
                    f"admin:menu:{course_slug}"
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )

def get_hint_selection_keyboard(
    course_slug: str,
    hints: list,
) -> InlineKeyboardMarkup:
    rows = []

    for hint in hints:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"💡 Hint {hint.number}",
                    callback_data=(
                        f"admin:add:hint:"
                        f"{hint.id}:"
                        f"{course_slug}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=(
                    f"admin:menu:{course_slug}"
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )

def get_schedule_confirm_keyboard(
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Запланировать",
                    callback_data="admin:add:confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=(
                        f"admin:menu:{course_slug}"
                    ),
                )
            ],
        ]
    )

def get_subscription_users_keyboard(
    users: list,
) -> InlineKeyboardMarkup:
    rows = []

    for user in users:
        if user.username:
            label = (
                f"@{user.username} "
                f"({user.telegram_id})"
            )
        else:
            label = str(
                user.telegram_id
            )

        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=(
                        f"admin:sub:user:"
                        f"{user.id}"
                    ),
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def get_subscription_confirm_keyboard(
    show_confirm: bool = True,
) -> InlineKeyboardMarkup:
    rows = []

    if show_confirm:
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=(
                        "admin:sub:confirm"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=(
                    "admin:sub:cancel"
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )