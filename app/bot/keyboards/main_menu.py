from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard(
    course_slug: str,
    requires_subscription: bool = True,
) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="📚 Проекты",
                callback_data=f"menu:projects:{course_slug}",
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Прогресс",
                callback_data=f"menu:progress:{course_slug}",
            ),
            InlineKeyboardButton(
                text="⭐ XP",
                callback_data=f"menu:xp:{course_slug}",
            ),
        ],
    ]

    if requires_subscription:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="💳 Подписка",
                    callback_data=f"menu:subscription:{course_slug}",
                )
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="ℹ️ О курсе",
                    callback_data=f"menu:about:{course_slug}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Сменить уровень",
                    callback_data="nav:courses",
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def get_back_to_menu_keyboard(course_slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"nav:menu:{course_slug}",
                )
            ]
        ]
    )