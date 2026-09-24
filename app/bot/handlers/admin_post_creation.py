from datetime import UTC, datetime
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import (
    parse_callback_int,
    parse_callback_int_str,
    parse_callback_str,
)
from app.bot.handlers.admin_common import (
    check_admin,
)
from app.bot.keyboards.admin import (
    get_hint_selection_keyboard,
    get_post_type_keyboard,
    get_project_selection_keyboard,
    get_schedule_confirm_keyboard,
)
from app.bot.states.admin import (
    AdminScheduleStates,
)
from app.config import get_app_timezone
from app.services.admin_service import (
    is_admin,
)
from app.services.schedule_service import (
    get_course_projects_for_schedule,
    get_project_hints_for_schedule,
)
from app.services.telegram_post_validation_service import (
    TelegramPostValidationError,
    build_telegram_post_preview,
    validate_telegram_post_content,
)
from app.utils.datetime_utils import (
    AmbiguousLocalTime,
    InvalidDateTimeFormat,
    NonexistentLocalTime,
    parse_local_datetime_to_utc,
)

router = Router()

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

    course_slug = parse_callback_str(
        callback.data,
        "admin:add:start",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

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

    course_slug = parse_callback_str(
        callback.data,
        "admin:add:type:regular",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

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

    course_slug = parse_callback_str(
        callback.data,
        "admin:add:type:project",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

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

    parsed = parse_callback_int_str(
        callback.data,
        "admin:add:project",
    )

    if parsed is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    project_id, course_slug = parsed

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

    course_slug = parse_callback_str(
        callback.data,
        "admin:add:type:hint",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

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

    hint_id = parse_callback_int(
        callback.data,
        "admin:add:hint",
    )

    if hint_id is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    await state.update_data(
        hint_id=hint_id,
        project_id=None,
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

    try:
        validate_telegram_post_content(
            content
        )

    except TelegramPostValidationError as error:
        await message.answer(
            "❌ <b>Публикацию нельзя "
            "сохранить.</b>\n\n"
            f"{escape(str(error))}"
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
            "<code>05.09.2026 18:30</code>\n\n"
            f"Часовой пояс: "
            f"<code>{escape(get_app_timezone())}</code>"
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
        scheduled_at = parse_local_datetime_to_utc(
            value,
            get_app_timezone(),
        )

    except InvalidDateTimeFormat:
        await message.answer(
            "❌ Неверный формат.\n\n"
            "Пример:\n"
            "<code>05.09.2026 18:30</code>"
        )
        return

    except NonexistentLocalTime:
        await message.answer(
            "❌ Такого местного времени "
            "не существует из-за перевода часов.\n\n"
            "Выбери другое время."
        )
        return

    except AmbiguousLocalTime:
        await message.answer(
            "❌ Это время встречается дважды "
            "из-за перевода часов.\n\n"
            "Выбери другое время."
        )
        return

    if scheduled_at <= datetime.now(UTC):
        await message.answer(
            "❌ Время должно быть в будущем."
        )
        return

    await state.update_data(
        scheduled_at=scheduled_at.isoformat()
    )

    data = await state.get_data()

    content_preview = (
        build_telegram_post_preview(
            data["content"],
            max_chars=2000,
        )
    )

    await state.set_state(
        AdminScheduleStates.confirming
    )

    await message.answer(
        text=(
            "📋 <b>Проверь публикацию</b>\n\n"
            f"Тип: <b>{data['post_type']}</b>\n"
            f"Время: <b>{value}</b>\n\n"
            "<b>Текст "
            "(предпросмотр):</b>\n\n"
            f"{escape(content_preview)}"
        ),
        reply_markup=get_schedule_confirm_keyboard(
            data["course_slug"]
        ),
    )