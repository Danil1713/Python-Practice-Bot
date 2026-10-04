from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import build_callback_data


def get_main_menu_keyboard(
    course_slug: str,
    requires_subscription: bool = True,
    has_channel: bool = False,
    is_admin_user: bool = False,
) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="📚 Проекты",
                callback_data=build_callback_data(
                    "menu",
                    "projects",
                    course_slug,
                ),
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Прогресс",
                callback_data=build_callback_data(
                    "menu",
                    "progress",
                    course_slug,
                ),
            ),
            InlineKeyboardButton(
                text="⭐ XP",
                callback_data=build_callback_data(
                    "menu",
                    "xp",
                    course_slug,
                ),
            ),
        ],
    ]

    if requires_subscription:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="💳 Подписка",
                    callback_data=build_callback_data(
                        "menu",
                        "subscription",
                        course_slug,
                    ),
                )
            ]
        )

    elif has_channel:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📢 Доступ к каналу",
                    callback_data=build_callback_data(
                        "subscription",
                        "channel",
                        course_slug,
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="ℹ️ О курсе",
                callback_data=build_callback_data(
                    "menu",
                    "about",
                    course_slug,
                ),
            )
        ],
    )
    if is_admin_user:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⚙️ Админ-панель",
                    callback_data=build_callback_data(
                        "admin",
                        "menu",
                        course_slug,
                    ),
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔄 Сменить уровень",
                callback_data="nav:courses",
            )
        ],
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_to_menu_keyboard(course_slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
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
        ]
    )
