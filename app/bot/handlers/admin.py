from html import escape

from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_admin_timezone

from app.bot.keyboards.admin import (
    get_admin_menu_keyboard,
    get_schedule_keyboard,
    get_scheduled_post_keyboard,
    get_admin_input_cancel_keyboard,
    get_post_type_keyboard,
    get_project_selection_keyboard,
    get_hint_selection_keyboard,
    get_schedule_confirm_keyboard, get_subscription_users_keyboard,
    get_subscription_confirm_keyboard,
)
from app.services.admin_service import (
    is_admin,
)
from app.services.admin_subscription_service import search_users, activate_or_extend_subscription_by_slug
from app.services.course_service import get_course_by_slug
from app.services.schedule_service import (
    ScheduledPostNotEditable,
    ScheduledPostNotFound,
    cancel_scheduled_post,
    get_course_schedule,
    get_scheduled_post_detail,
    publish_post_now,
    reschedule_post,
    get_course_projects_for_schedule,
    get_project_hints_for_schedule,
    ScheduleError,
    create_scheduled_post,
)
from app.bot.states.admin import (
    AdminScheduleStates,
)


router = Router()


async def check_admin(
    callback: CallbackQuery,
) -> bool:
    if is_admin(callback.from_user.id):
        return True

    await callback.answer(
        "⛔ Нет доступа.",
        show_alert=True,
    )

    return False

@router.callback_query(
    F.data.startswith("admin:menu:")
)
async def admin_menu_handler(
    callback: CallbackQuery,
) -> None:
    if not await check_admin(callback):
        return

    course_slug = callback.data.split(":")[2]

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
            "⚙️ <b>Админ-панель</b>\n\n"
            f"Курс: <b>{escape(course_slug)}</b>\n\n"
            "Здесь можно управлять "
            "публикациями курса."
        ),
        reply_markup=get_admin_menu_keyboard(
            course_slug,
            course.requires_subscription
        ),
    )

    await callback.answer()

@router.callback_query(
    F.data.startswith("admin:schedule:")
)
async def admin_schedule_handler(
    callback: CallbackQuery,
) -> None:
    if not await check_admin(callback):
        return

    course_slug = callback.data.split(":")[2]

    posts = await get_course_schedule(
        course_slug
    )

    lines = [
        "📅 <b>Расписание</b>",
        "",
    ]

    if not posts:
        lines.append(
            "Запланированных публикаций нет."
        )

    else:
        for post in posts:
            icon = (
                "🕒"
                if post.status == "scheduled"
                else "⚠️"
            )

            lines.append(
                f"{icon} #{post.id} — "
                f"{post.post_type}"
            )

            lines.append(
                "   "
                + format_admin_datetime(
                    post.scheduled_at
                )
            )

    await callback.message.edit_text(
        text="\n".join(lines),
        reply_markup=get_schedule_keyboard(
            course_slug,
            posts,
        ),
    )

    await callback.answer()

@router.callback_query(
    F.data.startswith("admin:post:")
)
async def admin_post_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    await state.clear()

    parts = callback.data.split(":")

    post_id = int(parts[2])
    course_slug = parts[3]

    post = await get_scheduled_post_detail(
        post_id
    )

    content_preview = post.content

    if len(content_preview) > 500:
        content_preview = (
            content_preview[:500]
            + "..."
        )

    text = (
        f"📝 <b>Публикация #{post.id}</b>\n\n"
        f"Тип: <b>{post.post_type}</b>\n"
        f"Статус: <b>{post.status}</b>\n"
        f"Время: <b>"
        f"{format_admin_datetime(post.scheduled_at)}"
        f"</b>\n\n"
        f"<b>Содержимое:</b>\n"
        f"{escape(content_preview)}"
    )

    if post.error_message:
        text += (
            "\n\n⚠️ <b>Ошибка:</b>\n"
            + escape(post.error_message[:500])
        )

    await callback.message.edit_text(
        text=text,
        reply_markup=(
            get_scheduled_post_keyboard(
                post_id=post.id,
                course_slug=course_slug,
            )
        ),
    )

    await callback.answer()

@router.callback_query(
    F.data.startswith("admin:publish:")
)
async def admin_publish_now_handler(
    callback: CallbackQuery,
    bot: Bot,
) -> None:
    if not await check_admin(callback):
        return

    parts = callback.data.split(":")

    post_id = int(parts[2])
    course_slug = parts[3]

    try:
        await publish_post_now(
            post_id=post_id,
            bot=bot,
        )

    except ScheduledPostNotFound:
        await callback.answer(
            "Публикация не найдена.",
            show_alert=True,
        )
        return

    except ScheduledPostNotEditable as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    await callback.answer(
        "✅ Опубликовано.",
        show_alert=True,
    )

    posts = await get_course_schedule(
        course_slug
    )

    await callback.message.edit_text(
        text=(
            "📅 <b>Расписание</b>\n\n"
            "Публикация успешно отправлена."
        ),
        reply_markup=get_schedule_keyboard(
            course_slug,
            posts,
        ),
    )

@router.callback_query(
    F.data.startswith("admin:cancel:")
)
async def admin_cancel_post_handler(
    callback: CallbackQuery,
) -> None:
    if not await check_admin(callback):
        return

    parts = callback.data.split(":")

    post_id = int(parts[2])
    course_slug = parts[3]

    try:
        await cancel_scheduled_post(
            post_id
        )

    except ScheduledPostNotFound:
        await callback.answer(
            "Публикация не найдена.",
            show_alert=True,
        )
        return

    except ScheduledPostNotEditable as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    posts = await get_course_schedule(
        course_slug
    )

    await callback.message.edit_text(
        text=(
            "📅 <b>Расписание</b>\n\n"
            "❌ Публикация отменена."
        ),
        reply_markup=get_schedule_keyboard(
            course_slug,
            posts,
        ),
    )

    await callback.answer()

@router.callback_query(
    F.data.startswith("admin:reschedule:")
)
async def admin_reschedule_start_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    parts = callback.data.split(":")

    post_id = int(parts[2])
    course_slug = parts[3]

    await state.set_state(
        AdminScheduleStates
        .waiting_for_reschedule_datetime
    )

    await state.update_data(
        post_id=post_id,
        course_slug=course_slug,
    )

    await callback.message.edit_text(
        text=(
            "🕒 <b>Перенос публикации</b>\n\n"
            "Отправь новую дату и время "
            "в формате:\n\n"
            "<code>05.09.2026 18:30</code>\n\n"
            "Время указывай по своему "
            "местному времени."
        ),
        reply_markup=get_admin_input_cancel_keyboard(
            post_id=post_id,
            course_slug=course_slug,
        ),
    )

    await callback.answer()

@router.message(
    AdminScheduleStates
    .waiting_for_reschedule_datetime
)
async def admin_reschedule_datetime_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    value = (message.text or "").strip()

    try:
        local_datetime = datetime.strptime(
            value,
            "%d.%m.%Y %H:%M",
        )

    except ValueError:
        await message.answer(
            "❌ Неверный формат.\n\n"
            "Используй:\n"
            "<code>05.09.2026 18:30</code>"
        )
        return

    timezone = ZoneInfo(
        get_admin_timezone()
    )

    local_datetime = (
        local_datetime.replace(
            tzinfo=timezone
        )
    )

    scheduled_at = (
        local_datetime.astimezone(
            ZoneInfo("UTC")
        )
    )

    data = await state.get_data()

    post_id = data["post_id"]
    course_slug = data["course_slug"]

    try:
        await reschedule_post(
            post_id=post_id,
            scheduled_at=scheduled_at,
        )

    except (
        ScheduledPostNotFound,
        ScheduledPostNotEditable,
    ) as error:
        await state.clear()

        await message.answer(
            f"❌ {error}"
        )
        return

    await state.clear()

    posts = await get_course_schedule(
        course_slug
    )

    await message.answer(
        text=(
            "✅ <b>Публикация перенесена.</b>\n\n"
            f"Новое время: "
            f"<b>{value}</b>"
        ),
        reply_markup=get_schedule_keyboard(
            course_slug,
            posts,
        ),
    )

def format_admin_datetime(
    value: datetime,
) -> str:
    timezone = ZoneInfo(
        get_admin_timezone()
    )

    local_value = value.astimezone(
        timezone
    )

    return local_value.strftime(
        "%d.%m.%Y %H:%M"
    )

@router.callback_query(
    F.data.startswith("admin:add:start:")
)
async def admin_add_post_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    await state.clear()

    course_slug = callback.data.split(":")[3]

    await state.set_state(
        AdminScheduleStates.choosing_post_type
    )

    await state.update_data(
        course_slug=course_slug
    )

    await callback.message.edit_text(
        text=(
            "➕ <b>Новая публикация</b>\n\n"
            "Выбери тип публикации:"
        ),
        reply_markup=get_post_type_keyboard(
            course_slug
        ),
    )

    await callback.answer()

@router.callback_query(
    AdminScheduleStates.choosing_post_type,
    F.data.startswith(
        "admin:add:type:regular:"
    ),
)
async def admin_add_regular_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    course_slug = callback.data.split(":")[4]

    await state.update_data(
        course_slug=course_slug,
        post_type="regular",
        project_id=None,
        hint_id=None,
    )

    await state.set_state(
        AdminScheduleStates.waiting_for_content
    )

    await callback.message.edit_text(
        text=(
            "📝 <b>Обычный пост</b>\n\n"
            "Отправь текст публикации."
        )
    )

    await callback.answer()

@router.callback_query(
    AdminScheduleStates.choosing_post_type,
    F.data.startswith(
        "admin:add:type:project:"
    ),
)

async def admin_add_project_type_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    course_slug = callback.data.split(":")[4]

    projects = await get_course_projects_for_schedule(
        course_slug
    )

    await state.set_state(
        AdminScheduleStates.choosing_project
    )

    await state.update_data(
        course_slug=course_slug,
        post_type="project",
    )

    await callback.message.edit_text(
        text=(
            "🚀 <b>Выбери Project</b>"
        ),
        reply_markup=get_project_selection_keyboard(
            course_slug,
            projects,
        ),
    )

    await callback.answer()

@router.callback_query(
    AdminScheduleStates.choosing_project,
    F.data.startswith(
        "admin:add:project:"
    ),
)
async def admin_add_project_select_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    parts = callback.data.split(":")

    project_id = int(parts[3])
    course_slug = parts[4]

    data = await state.get_data()

    post_type = data["post_type"]

    await state.update_data(
        project_id=project_id,
    )

    if post_type == "project":
        await state.update_data(
            hint_id=None
        )

        await state.set_state(
            AdminScheduleStates.waiting_for_content
        )

        await callback.message.edit_text(
            text=(
                "🚀 <b>Project выбран.</b>\n\n"
                "Теперь отправь текст поста."
            )
        )

    elif post_type == "hint":
        hints = (
            await get_project_hints_for_schedule(
                project_id
            )
        )

        await state.set_state(
            AdminScheduleStates.choosing_hint
        )

        await callback.message.edit_text(
            text=(
                "💡 <b>Выбери Hint</b>"
            ),
            reply_markup=get_hint_selection_keyboard(
                course_slug=course_slug,
                hints=hints,
            ),
        )

    await callback.answer()

    await callback.answer()

@router.callback_query(
    AdminScheduleStates.choosing_post_type,
    F.data.startswith(
        "admin:add:type:hint:"
    ),
)
async def admin_add_hint_type_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    course_slug = callback.data.split(":")[4]

    projects = await get_course_projects_for_schedule(
        course_slug
    )

    await state.set_state(
        AdminScheduleStates.choosing_project
    )

    await state.update_data(
        course_slug=course_slug,
        post_type="hint",
    )

    await callback.message.edit_text(
        text=(
            "💡 <b>Для какого Project "
            "создать Hint?</b>"
        ),
        reply_markup=get_project_selection_keyboard(
            course_slug,
            projects,
        ),
    )

    await callback.answer()

@router.callback_query(
    AdminScheduleStates.choosing_hint,
    F.data.startswith(
        "admin:add:hint:"
    ),
)
async def admin_add_hint_select_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    parts = callback.data.split(":")

    hint_id = int(parts[3])

    await state.update_data(
        hint_id=hint_id
    )

    await state.set_state(
        AdminScheduleStates.waiting_for_content
    )

    await callback.message.edit_text(
        text=(
            "💡 <b>Hint выбран.</b>\n\n"
            "Теперь отправь текст поста."
        )
    )

    await callback.answer()

@router.message(
    AdminScheduleStates.waiting_for_content
)
async def admin_add_content_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    content = message.html_text

    if not content.strip():
        await message.answer(
            "❌ Текст публикации пустой."
        )
        return

    await state.update_data(
        content=content
    )

    await state.set_state(
        AdminScheduleStates.waiting_for_datetime
    )

    await message.answer(
        text=(
            "🕒 <b>Когда опубликовать?</b>\n\n"
            "Отправь дату и время:\n\n"
            "<code>05.09.2026 18:30</code>"
        )
    )

@router.message(
    AdminScheduleStates.waiting_for_datetime
)
async def admin_add_datetime_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    value = (message.text or "").strip()

    try:
        local_datetime = datetime.strptime(
            value,
            "%d.%m.%Y %H:%M",
        )

    except ValueError:
        await message.answer(
            "❌ Неверный формат.\n\n"
            "Пример:\n"
            "<code>05.09.2026 18:30</code>"
        )
        return

    timezone = ZoneInfo(
        get_admin_timezone()
    )

    scheduled_at = (
        local_datetime
        .replace(tzinfo=timezone)
        .astimezone(ZoneInfo("UTC"))
    )

    if scheduled_at <= datetime.now(
        ZoneInfo("UTC")
    ):
        await message.answer(
            "❌ Время должно быть в будущем."
        )
        return

    await state.update_data(
        scheduled_at=scheduled_at
    )

    data = await state.get_data()

    await state.set_state(
        AdminScheduleStates.confirming
    )

    await message.answer(
        text=(
            "📋 <b>Проверь публикацию</b>\n\n"
            f"Тип: <b>{data['post_type']}</b>\n"
            f"Время: <b>{value}</b>\n\n"
            "<b>Текст:</b>\n\n"
            f"{data['content']}"
        ),
        reply_markup=get_schedule_confirm_keyboard(
            data["course_slug"]
        ),
    )

@router.callback_query(
    AdminScheduleStates.confirming,
    F.data == "admin:add:confirm",
)
async def admin_add_confirm_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    data = await state.get_data()

    try:
        post = await create_scheduled_post(
            course_slug=data["course_slug"],
            post_type=data["post_type"],
            content=data["content"],
            scheduled_at=data["scheduled_at"],
            project_id=data.get("project_id"),
            hint_id=data.get("hint_id"),
        )

    except ScheduleError as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    course_slug = data["course_slug"]

    await state.clear()

    posts = await get_course_schedule(
        course_slug
    )

    await callback.message.edit_text(
        text=(
            "✅ <b>Публикация "
            "запланирована.</b>\n\n"
            f"ID: <b>#{post.id}</b>\n"
            f"Время: <b>"
            f"{format_admin_datetime(post.scheduled_at)}"
            f"</b>"
        ),
        reply_markup=get_schedule_keyboard(
            course_slug,
            posts,
        ),
    )

    await callback.answer()

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

    course_slug = callback.data.split(":")[2]

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
            "или username."
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
            reply_markup=get_subscription_confirm_keyboard(
                show_confirm=False
            ),
        )

        return

    users = await search_users(
        value
    )

    if not users:
        await message.answer(
            text=(
                "❌ <b>Пользователь не найден.</b>\n\n"
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

    user_id = int(
        callback.data.split(":")[3]
    )

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
            "❌ Введи целое число."
        )
        return

    if days <= 0:
        await message.answer(
            "❌ Количество дней должно "
            "быть больше 0."
        )
        return

    await state.update_data(
        subscription_days=days
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
            f"{data['subscription_course_slug']}"
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
        )
    )

    course_slug = data["subscription_course_slug"]

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
            "✅ <b>Подписка активирована.</b>\n\n"
            f"Курс: <b>{escape(course.title)}</b>\n"
            f"До: <b>"
            f"{format_admin_datetime(result.ends_at)}"
            f"</b>\n\n"
            "Можно продолжить работу "
            "в админ-панели."
        ),
        reply_markup=get_admin_menu_keyboard(
            course_slug=course.slug,
            requires_subscription=(
                course.requires_subscription
            ),
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
            "❌ <b>Выдача подписки отменена.</b>\n\n"
            f"Курс: <b>{escape(course.title)}</b>\n\n"
            "Можно продолжить работу "
            "в админ-панели."
        ),
        reply_markup=get_admin_menu_keyboard(
            course_slug=course.slug,
            requires_subscription=(
                course.requires_subscription
            ),
        ),
    )

    await callback.answer()