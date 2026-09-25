from html import escape
from uuid import uuid4

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import (
    parse_callback_int,
    parse_callback_str,
)
from app.bot.handlers.admin_common import (
    check_admin,
    format_admin_datetime,
)
from app.bot.keyboards.admin import (
    get_admin_menu_keyboard,
    get_subscription_confirm_keyboard,
    get_subscription_users_keyboard,
)
from app.bot.states.admin import (
    AdminScheduleStates,
)
from app.services.admin_service import (
    is_admin,
)
from app.services.admin_subscription_service import (
    activate_or_extend_subscription_by_slug,
    search_users,
)
from app.services.course_service import (
    get_course_by_slug,
)

router = Router()


@router.callback_query(
    F.data.startswith(
        "admin:subscriptions:"
    )
)
async def admin_subscriptions_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    await state.clear()

    course_slug = parse_callback_str(
        callback.data,
        "admin:subscriptions",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    await state.set_state(
        AdminScheduleStates
        .searching_subscription_user
    )

    await state.update_data(
        subscription_course_slug=course_slug,
        return_course_slug=course_slug,
    )

    await callback.message.edit_text(
        text=(
            "👤 <b>Управление подпиской</b>\n\n"
            f"Курс: <b>{escape(course_slug)}</b>\n\n"
            "Отправь Telegram ID пользователя "
            "или username обязательно с @.\n\n"
            "Примеры:\n"
            "<code>123456789</code>\n"
            "<code>@username</code>"
        ),
        reply_markup=(
            get_subscription_confirm_keyboard(
                show_confirm=False
            )
        ),
    )

    await callback.answer()


@router.message(
    AdminScheduleStates
    .searching_subscription_user
)
async def admin_subscription_search_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not is_admin(
        message.from_user.id
    ):
        await state.clear()
        return

    value = (
        message.text or ""
    ).strip()

    if not value:
        await message.answer(
            "❌ Введи Telegram ID "
            "или username.",
            reply_markup=(
                get_subscription_confirm_keyboard(
                    show_confirm=False
                )
            ),
        )
        return

    if (
        not value.isdigit()
        and not value.startswith("@")
    ):
        await message.answer(
            text=(
                "❌ <b>Username нужно вводить "
                "с символом @.</b>\n\n"
                "Например:\n"
                "<code>@username</code>\n\n"
                "Либо отправь Telegram ID."
            ),
            reply_markup=(
                get_subscription_confirm_keyboard(
                    show_confirm=False
                )
            ),
        )
        return

    users = await search_users(
        value
    )

    if not users:
        await message.answer(
            text=(
                "❌ <b>Пользователь "
                "не найден.</b>\n\n"
                "Проверь Telegram ID "
                "или username и попробуй ещё раз."
            ),
            reply_markup=(
                get_subscription_confirm_keyboard(
                    show_confirm=False
                )
            ),
        )
        return

    await state.set_state(
        AdminScheduleStates
        .choosing_subscription_user
    )

    await message.answer(
        text="Выбери пользователя:",
        reply_markup=(
            get_subscription_users_keyboard(
                users
            )
        ),
    )


@router.callback_query(
    AdminScheduleStates
    .choosing_subscription_user,
    F.data.startswith(
        "admin:sub:user:"
    ),
)
async def admin_subscription_user_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    user_id = parse_callback_int(
        callback.data,
        "admin:sub:user",
    )

    if user_id is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    await state.update_data(
        subscription_user_id=user_id
    )

    data = await state.get_data()

    await state.set_state(
        AdminScheduleStates
        .waiting_for_subscription_days
    )

    await callback.message.edit_text(
        text=(
            "📅 <b>На сколько дней "
            "выдать подписку?</b>\n\n"
            f"Курс: <b>"
            f"{escape(data['subscription_course_slug'])}"
            f"</b>\n\n"
            "Отправь число, например:\n"
            "<code>30</code>"
        ),
        reply_markup=(
            get_subscription_confirm_keyboard(
                show_confirm=False
            )
        ),
    )

    await callback.answer()


@router.message(
    AdminScheduleStates
    .waiting_for_subscription_days
)
async def admin_subscription_days_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not is_admin(
        message.from_user.id
    ):
        await state.clear()
        return

    value = (
        message.text or ""
    ).strip()

    try:
        days = int(value)

    except ValueError:
        await message.answer(
            "❌ Введи целое число.",
            reply_markup=(
                get_subscription_confirm_keyboard(
                    show_confirm=False
                )
            ),
        )
        return

    if days <= 0:
        await message.answer(
            "❌ Количество дней должно "
            "быть больше 0.",
            reply_markup=(
                get_subscription_confirm_keyboard(
                    show_confirm=False
                )
            ),
        )
        return

    await state.update_data(
        subscription_days=days,
        subscription_idempotency_key=(
            uuid4().hex
        ),
    )

    data = await state.get_data()

    await state.set_state(
        AdminScheduleStates
        .confirming_subscription
    )

    await message.answer(
        text=(
            "📋 <b>Подтверждение</b>\n\n"
            f"Курс: <b>"
            f"{escape(data['subscription_course_slug'])}"
            f"</b>\n"
            f"Срок: <b>{days} дней</b>\n\n"
            "Выдать / продлить подписку?"
        ),
        reply_markup=(
            get_subscription_confirm_keyboard()
        ),
    )


@router.callback_query(
    AdminScheduleStates
    .confirming_subscription,
    F.data == "admin:sub:confirm",
)
async def admin_subscription_confirm_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    data = await state.get_data()

    idempotency_key = data.get(
        "subscription_idempotency_key"
    )

    if not idempotency_key:
        await callback.answer(
            "Операция устарела. "
            "Начните выдачу подписки заново.",
            show_alert=True,
        )
        return

    result = (
        await activate_or_extend_subscription_by_slug(
            user_id=data[
                "subscription_user_id"
            ],
            course_slug=data[
                "subscription_course_slug"
            ],
            days=data[
                "subscription_days"
            ],
            actor_telegram_id=(
                callback.from_user.id
            ),
            idempotency_key=(
                idempotency_key
            ),
        )
    )

    course_slug = data[
        "subscription_course_slug"
    ]

    await state.clear()

    course = await get_course_by_slug(
        course_slug
    )

    if course is None:
        await callback.answer(
            "Курс не найден.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        text=(
            "✅ <b>Подписка "
            "активирована.</b>\n\n"
            f"Курс: <b>"
            f"{escape(course.title)}"
            f"</b>\n"
            f"До: <b>"
            f"{format_admin_datetime(result.ends_at)}"
            f"</b>\n\n"
            "Можно продолжить работу "
            "в админ-панели."
        ),
        reply_markup=(
            get_admin_menu_keyboard(
                course_slug=course.slug,
                requires_subscription=(
                    course.requires_subscription
                ),
            )
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data == "admin:sub:cancel"
)
async def admin_subscription_cancel_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    data = await state.get_data()

    course_slug = data.get(
        "subscription_course_slug"
    )

    await state.clear()

    if course_slug is None:
        await callback.message.edit_text(
            "❌ Выдача подписки отменена."
        )

        await callback.answer()
        return

    course = await get_course_by_slug(
        course_slug
    )

    if course is None:
        await callback.message.edit_text(
            "❌ Выдача подписки отменена."
        )

        await callback.answer()
        return

    await callback.message.edit_text(
        text=(
            "❌ <b>Выдача подписки "
            "отменена.</b>\n\n"
            f"Курс: <b>"
            f"{escape(course.title)}"
            f"</b>\n\n"
            "Можно продолжить работу "
            "в админ-панели."
        ),
        reply_markup=(
            get_admin_menu_keyboard(
                course_slug=course.slug,
                requires_subscription=(
                    course.requires_subscription
                ),
            )
        ),
    )

    await callback.answer()