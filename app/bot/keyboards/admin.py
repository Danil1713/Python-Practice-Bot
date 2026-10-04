from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.bot.callbacks import (
    build_callback_data,
)


def get_admin_menu_keyboard(
    course_slug: str,
    requires_subscription: bool,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="📅 Расписание",
                callback_data=build_callback_data(
                    "admin",
                    "schedule",
                    course_slug,
                ),
            )
        ],
        [
            InlineKeyboardButton(
                text="➕ Добавить публикацию",
                callback_data=build_callback_data(
                    "admin",
                    "add",
                    "start",
                    course_slug,
                ),
            )
        ],
    ]

    if requires_subscription:
        rows.append(
            [
                InlineKeyboardButton(
                    text="👤 Подписки",
                    callback_data=build_callback_data(
                        "admin",
                        "subscriptions",
                        course_slug,
                    ),
                )
            ]
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text="💳 Платежи на проверке",
                    callback_data=build_callback_data(
                        "admin",
                        "payreview",
                        course_slug,
                    ),
                )
            ]
        )

    rows.append(
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

    return InlineKeyboardMarkup(inline_keyboard=rows)


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
                    text=(f"{status_icon} {type_icon} #{post.id}"),
                    callback_data=build_callback_data(
                        "admin",
                        "post",
                        post.id,
                        course_slug,
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="➕ Добавить",
                callback_data=build_callback_data(
                    "admin",
                    "add",
                    "start",
                    course_slug,
                ),
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=build_callback_data(
                    "admin",
                    "menu",
                    course_slug,
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_scheduled_post_keyboard(
    post_id: int,
    course_slug: str,
    status: str,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="🚀 Опубликовать сейчас",
                callback_data=build_callback_data(
                    "admin",
                    "publish",
                    post_id,
                    course_slug,
                ),
            )
        ]
    ]

    if status in {
        "scheduled",
        "failed",
    }:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🕒 Перенести",
                    callback_data=build_callback_data(
                        "admin",
                        "reschedule",
                        post_id,
                        course_slug,
                    ),
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=build_callback_data(
                        "admin",
                        "cancel",
                        post_id,
                        course_slug,
                    ),
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=build_callback_data(
                    "admin",
                    "schedule",
                    course_slug,
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_publish_post_confirm_keyboard(
    post_id: int,
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, опубликовать",
                    callback_data=build_callback_data(
                        "admin",
                        "publish",
                        "confirm",
                        post_id,
                        course_slug,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Нет, вернуться",
                    callback_data=build_callback_data(
                        "admin",
                        "post",
                        post_id,
                        course_slug,
                    ),
                )
            ],
        ]
    )


def get_cancel_post_confirm_keyboard(
    post_id: int,
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, отменить",
                    callback_data=build_callback_data(
                        "admin",
                        "cancel",
                        "confirm",
                        post_id,
                        course_slug,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Нет, вернуться",
                    callback_data=build_callback_data(
                        "admin",
                        "post",
                        post_id,
                        course_slug,
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
                    callback_data=build_callback_data(
                        "admin",
                        "post",
                        post_id,
                        course_slug,
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
                    callback_data=build_callback_data(
                        "admin",
                        "add",
                        "type",
                        "regular",
                        course_slug,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚀 Project",
                    callback_data=build_callback_data(
                        "admin",
                        "add",
                        "type",
                        "project",
                        course_slug,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="💡 Hint",
                    callback_data=build_callback_data(
                        "admin",
                        "add",
                        "type",
                        "hint",
                        course_slug,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=build_callback_data(
                        "admin",
                        "menu",
                        course_slug,
                    ),
                )
            ],
        ]
    )


def get_project_selection_keyboard(
    course_slug: str,
    projects: list,
    allow_create: bool = False,
) -> InlineKeyboardMarkup:
    rows = []

    for project in projects:
        rows.append(
            [
                InlineKeyboardButton(
                    text=(f"Project {project.number} — {project.title}"),
                    callback_data=build_callback_data(
                        "admin",
                        "add",
                        "project",
                        project.id,
                        course_slug,
                    ),
                )
            ]
        )

    if allow_create:
        rows.append(
            [
                InlineKeyboardButton(
                    text="➕ Создать проект",
                    callback_data=build_callback_data(
                        "admin",
                        "create",
                        "project",
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=build_callback_data(
                    "admin",
                    "add",
                    "start",
                    course_slug,
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_hint_selection_keyboard(
    course_slug: str,
    hints,
    allow_create: bool = True,
) -> InlineKeyboardMarkup:
    rows = []

    for hint in hints:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"💡 Hint {hint.number}",
                    callback_data=build_callback_data(
                        "admin",
                        "add",
                        "hint",
                        hint.id,
                    ),
                )
            ]
        )

    if allow_create:
        rows.append(
            [
                InlineKeyboardButton(
                    text="➕ Создать подсказку",
                    callback_data=build_callback_data(
                        "admin",
                        "create",
                        "hint",
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=build_callback_data(
                    "admin",
                    "add",
                    "hint-projects",
                    course_slug,
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


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
                    callback_data=build_callback_data(
                        "admin",
                        "menu",
                        course_slug,
                    ),
                )
            ],
        ]
    )


def get_admin_add_cancel_keyboard(
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=build_callback_data(
                        "admin",
                        "menu",
                        course_slug,
                    ),
                )
            ]
        ]
    )


def get_subscription_users_keyboard(
    users: list,
) -> InlineKeyboardMarkup:
    rows = []

    for user in users:
        if user.username:
            label = f"@{user.username} ({user.telegram_id})"
        else:
            label = str(user.telegram_id)

        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=build_callback_data(
                        "admin",
                        "sub",
                        "user",
                        user.id,
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=build_callback_data(
                    "admin",
                    "sub",
                    "cancel",
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_subscription_confirm_keyboard(
    show_confirm: bool = True,
) -> InlineKeyboardMarkup:
    rows = []

    if show_confirm:
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=("admin:sub:confirm"),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=("admin:sub:cancel"),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_project_creation_input_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить создание",
                    callback_data=build_callback_data(
                        "admin",
                        "create",
                        "project",
                        "cancel",
                    ),
                )
            ]
        ]
    )


def get_project_creation_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Создать проект",
                    callback_data=build_callback_data(
                        "admin",
                        "create",
                        "project",
                        "confirm",
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить создание",
                    callback_data=build_callback_data(
                        "admin",
                        "create",
                        "project",
                        "cancel",
                    ),
                )
            ],
        ]
    )


def get_hint_creation_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Создать подсказку",
                    callback_data=build_callback_data(
                        "admin",
                        "create",
                        "hint",
                        "confirm",
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить создание",
                    callback_data=build_callback_data(
                        "admin",
                        "create",
                        "hint",
                        "cancel",
                    ),
                )
            ],
        ]
    )


def get_review_payments_keyboard(
    course_slug: str,
    payments: list,
) -> InlineKeyboardMarkup:
    rows = []

    for payment in payments:
        if payment.username:
            user_label = f"@{payment.username}"
        else:
            user_label = str(payment.telegram_user_id)

        rows.append(
            [
                InlineKeyboardButton(
                    text=(f"⚠️ #{payment.id} — {user_label}"),
                    callback_data=build_callback_data(
                        "admin",
                        "payreview-item",
                        payment.id,
                        course_slug,
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=build_callback_data(
                    "admin",
                    "menu",
                    course_slug,
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_review_payment_keyboard(
    *,
    payment_id: int,
    course_slug: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Повторить активацию",
                    callback_data=build_callback_data(
                        "admin",
                        "payreview-retry",
                        payment_id,
                        course_slug,
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=build_callback_data(
                        "admin",
                        "payreview",
                        course_slug,
                    ),
                )
            ],
        ]
    )
