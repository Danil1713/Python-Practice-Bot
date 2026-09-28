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
    format_admin_datetime,
)
from app.bot.keyboards.admin import (
    get_admin_add_cancel_keyboard,
    get_hint_creation_confirm_keyboard,
    get_hint_selection_keyboard,
    get_post_type_keyboard,
    get_project_creation_confirm_keyboard,
    get_project_creation_input_keyboard,
    get_project_selection_keyboard,
    get_schedule_confirm_keyboard,
    get_schedule_keyboard,
)
from app.bot.states.admin import (
    AdminScheduleStates,
)
from app.config import get_app_timezone
from app.services.admin_service import (
    is_admin,
)
from app.services.hint_service import (
    HintCreationError,
    can_create_hint,
    create_hint,
)
from app.services.project_service import (
    ProjectCreationError,
    create_project,
)
from app.services.schedule_service import (
    ScheduleError,
    create_scheduled_post,
    get_course_projects_for_hint_schedule,
    get_course_projects_for_schedule,
    get_course_schedule,
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


async def _show_project_selection(
    message: Message,
    state: FSMContext,
    course_slug: str,
) -> None:
    projects = await get_course_projects_for_schedule(
        course_slug
    )

    await state.set_state(
        AdminScheduleStates.choosing_project
    )

    await state.update_data(
        course_slug=course_slug,
        post_type="project",
        project_id=None,
        hint_id=None,
    )

    await message.edit_text(
        text="🚀 <b>Выбери Project</b>",
        reply_markup=get_project_selection_keyboard(
            course_slug,
            projects,
            allow_create=True,
        ),
    )


async def _show_hint_project_selection(
    message: Message,
    state: FSMContext,
    course_slug: str,
) -> None:
    projects = (
        await get_course_projects_for_hint_schedule(
            course_slug
        )
    )

    await state.set_state(
        AdminScheduleStates.choosing_project
    )

    await state.update_data(
        course_slug=course_slug,
        post_type="hint",
        project_id=None,
        hint_id=None,
    )

    await message.edit_text(
        text=(
            "💡 <b>Для какого Project "
            "создать Hint?</b>"
        ),
        reply_markup=get_project_selection_keyboard(
            course_slug,
            projects,
        ),
    )


async def _show_hint_selection(
    message: Message,
    state: FSMContext,
    course_slug: str,
    project_id: int,
) -> None:
    hints = await get_project_hints_for_schedule(
        project_id
    )

    allow_create = await can_create_hint(
        project_id
    )

    await state.set_state(
        AdminScheduleStates.choosing_hint
    )

    await state.update_data(
        course_slug=course_slug,
        post_type="hint",
        project_id=project_id,
        hint_id=None,
    )

    await message.edit_text(
        text="💡 <b>Выбери Hint</b>",
        reply_markup=get_hint_selection_keyboard(
            course_slug=course_slug,
            hints=hints,
            allow_create=allow_create,
        ),
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

    data = await state.get_data()

    state_course_slug = data.get(
        "course_slug"
    )

    if (
            not isinstance(
                state_course_slug,
                str,
            )
            or state_course_slug != course_slug
    ):
        await callback.answer(
            "Контекст публикации изменился.",
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
        ),
        reply_markup=get_admin_add_cancel_keyboard(
            course_slug
        ),
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

    data = await state.get_data()

    state_course_slug = data.get(
        "course_slug"
    )

    if (
            not isinstance(
                state_course_slug,
                str,
            )
            or state_course_slug != course_slug
    ):
        await callback.answer(
            "Контекст публикации изменился.",
            show_alert=True,
        )
        return

    await _show_project_selection(
        callback.message,
        state,
        course_slug,
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

    project_id, callback_course_slug = parsed

    data = await state.get_data()

    course_slug = data.get("course_slug")
    post_type = data.get("post_type")

    if (
            not isinstance(course_slug, str)
            or callback_course_slug != course_slug
            or post_type not in {
        "project",
        "hint",
    }
    ):
        await callback.answer(
            "Контекст публикации изменился.",
            show_alert=True,
        )
        return

    try:
        if post_type == "project":
            projects = await get_course_projects_for_schedule(
                course_slug
            )
        else:
            projects = (
                await get_course_projects_for_hint_schedule(
                    course_slug
                )
            )

    except ScheduleError as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    if not any(
            project.id == project_id
            for project in projects
    ):
        await callback.answer(
            "Этот Project недоступен "
            "для текущей публикации.",
            show_alert=True,
        )
        return

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
            ),
            reply_markup=get_admin_add_cancel_keyboard(
                course_slug
            ),
        )


    elif post_type == "hint":

        await _show_hint_selection(
            callback.message,
            state,
            course_slug,
            project_id,
        )

    await callback.answer()


@router.callback_query(
    AdminScheduleStates.choosing_project,
    F.data == "admin:create:project",
)
async def admin_create_project_start_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    data = await state.get_data()

    course_slug = data.get("course_slug")
    post_type = data.get("post_type")

    if (
        not isinstance(course_slug, str)
        or post_type != "project"
    ):
        await callback.answer(
            "Контекст создания проекта потерян.",
            show_alert=True,
        )
        return

    await state.update_data(
        project_title=None,
        project_ai_requirements=None,
    )

    await state.set_state(
        AdminScheduleStates.creating_project_title
    )

    await callback.message.edit_text(
        "📦 <b>Создание Project</b>\n\n"
        "Введите название проекта.",
        reply_markup=(
            get_project_creation_input_keyboard()
        ),
    )

    await callback.answer()


@router.message(
    AdminScheduleStates.creating_project_title
)
async def admin_create_project_title_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if (
        message.from_user is None
        or not is_admin(message.from_user.id)
    ):
        return

    if message.text is None:
        await message.answer(
            "Название Project нужно отправить текстом.",
            reply_markup=(
                get_project_creation_input_keyboard()
            ),
        )
        return

    title = message.text.strip()

    if not title:
        await message.answer(
            "Название Project не может быть пустым.",
            reply_markup=(
                get_project_creation_input_keyboard()
            ),
        )
        return

    if len(title) > 255:
        await message.answer(
            "Название Project не должно превышать "
            "255 символов.",
            reply_markup=(
                get_project_creation_input_keyboard()
            ),
        )
        return

    await state.update_data(
        project_title=title
    )

    await state.set_state(
        AdminScheduleStates
        .creating_project_ai_requirements
    )

    await message.answer(
        "📋 <b>Обязательные критерии</b>\n\n"
        "Отправьте критерии, по которым AI должен "
        "проверять решение.",
        reply_markup=(
            get_project_creation_input_keyboard()
        ),
    )


@router.callback_query(
    AdminScheduleStates.choosing_hint,
    F.data.startswith(
        "admin:add:hint-projects:"
    ),
)
async def admin_add_hint_projects_back_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    course_slug = parse_callback_str(
        callback.data,
        "admin:add:hint-projects",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    data = await state.get_data()

    if (
        data.get("course_slug") != course_slug
        or data.get("post_type") != "hint"
    ):
        await callback.answer(
            "Контекст публикации изменился.",
            show_alert=True,
        )
        return

    await _show_hint_project_selection(
        callback.message,
        state,
        course_slug,
    )

    await callback.answer()


@router.message(
    AdminScheduleStates.creating_project_ai_requirements
)
async def admin_create_project_requirements_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if (
        message.from_user is None
        or not is_admin(message.from_user.id)
    ):
        return

    if message.text is None:
        await message.answer(
            "Обязательные критерии нужно отправить "
            "текстом.",
            reply_markup=(
                get_project_creation_input_keyboard()
            ),
        )
        return

    ai_requirements = message.text.strip()

    if not ai_requirements:
        await message.answer(
            "Обязательные критерии не могут "
            "быть пустыми.",
            reply_markup=(
                get_project_creation_input_keyboard()
            ),
        )
        return

    data = await state.get_data()

    title = data.get("project_title")
    course_slug = data.get("course_slug")

    if (
        not isinstance(title, str)
        or not isinstance(course_slug, str)
        or data.get("post_type") != "project"
    ):
        await state.clear()

        await message.answer(
            "Контекст создания Project потерян. "
            "Начните создание заново."
        )
        return

    await state.update_data(
        project_ai_requirements=ai_requirements
    )

    await state.set_state(
        AdminScheduleStates.confirming_project_creation
    )

    await message.answer(
        "📦 <b>Новый Project</b>\n\n"
        f"<b>Название:</b>\n{escape(title)}\n\n"
        "<b>Обязательные критерии:</b>\n"
        f"{escape(ai_requirements)}",
        reply_markup=(
            get_project_creation_confirm_keyboard()
        ),
    )


@router.callback_query(
    AdminScheduleStates.confirming_project_creation,
    F.data == "admin:create:project:confirm",
)
async def admin_create_project_confirm_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    data = await state.get_data()

    course_slug = data.get("course_slug")
    title = data.get("project_title")
    ai_requirements = data.get(
        "project_ai_requirements"
    )

    if (
        not isinstance(course_slug, str)
        or data.get("post_type") != "project"
        or not isinstance(title, str)
        or not isinstance(ai_requirements, str)
    ):
        await callback.answer(
            "Контекст создания Project потерян.",
            show_alert=True,
        )
        return

    try:
        project = await create_project(
            course_slug=course_slug,
            title=title,
            ai_requirements=ai_requirements,
        )
    except ProjectCreationError as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    await state.clear()

    await _show_project_selection(
        callback.message,
        state,
        course_slug,
    )

    await callback.answer(
        f"✅ Project {project.number} создан."
    )


@router.callback_query(
    AdminScheduleStates.creating_project_title,
    F.data == "admin:create:project:cancel",
)
@router.callback_query(
    AdminScheduleStates.creating_project_ai_requirements,
    F.data == "admin:create:project:cancel",
)
@router.callback_query(
    AdminScheduleStates.confirming_project_creation,
    F.data == "admin:create:project:cancel",
)
async def admin_create_project_cancel_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    data = await state.get_data()

    course_slug = data.get("course_slug")

    if (
        not isinstance(course_slug, str)
        or data.get("post_type") != "project"
    ):
        await state.clear()

        await callback.answer(
            "Контекст создания Project потерян.",
            show_alert=True,
        )
        return

    await state.clear()

    await _show_project_selection(
        callback.message,
        state,
        course_slug,
    )

    await callback.answer(
        "❌ Создание Project отменено."
    )


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

    data = await state.get_data()

    state_course_slug = data.get(
        "course_slug"
    )

    if (
            not isinstance(
                state_course_slug,
                str,
            )
            or state_course_slug != course_slug
    ):
        await callback.answer(
            "Контекст публикации изменился.",
            show_alert=True,
        )
        return

    await _show_hint_project_selection(
        callback.message,
        state,
        course_slug,
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

    data = await state.get_data()

    course_slug = data.get("course_slug")
    project_id = data.get("project_id")
    post_type = data.get("post_type")

    if (
            not isinstance(course_slug, str)
            or not isinstance(project_id, int)
            or post_type != "hint"
    ):
        await callback.answer(
            "Контекст публикации изменился.",
            show_alert=True,
        )
        return

    try:
        projects = (
            await get_course_projects_for_hint_schedule(
                course_slug
            )
        )

    except ScheduleError as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    if not any(
            project.id == project_id
            for project in projects
    ):
        await callback.answer(
            "Этот Project недоступен "
            "для публикации Hint.",
            show_alert=True,
        )
        return

    hints = await get_project_hints_for_schedule(
        project_id
    )

    if not any(
            hint.id == hint_id
            for hint in hints
    ):
        await callback.answer(
            "Этот Hint недоступен "
            "для публикации.",
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
        ),
        reply_markup=get_admin_add_cancel_keyboard(
            course_slug
        ),
    )

    await callback.answer()


@router.callback_query(
    AdminScheduleStates.choosing_hint,
    F.data == "admin:create:hint",
)
async def admin_create_hint_start_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    data = await state.get_data()

    course_slug = data.get("course_slug")
    project_id = data.get("project_id")

    if (
        not isinstance(course_slug, str)
        or data.get("post_type") != "hint"
        or not isinstance(project_id, int)
    ):
        await callback.answer(
            "Контекст создания подсказки потерян.",
            show_alert=True,
        )
        return

    await state.set_state(
        AdminScheduleStates.confirming_hint_creation
    )

    await callback.message.edit_text(
        "💡 <b>Создание Hint</b>\n\n"
        "Номер подсказки и XP после публикации "
        "будут определены автоматически.\n\n"
        "Создать следующую подсказку?",
        reply_markup=(
            get_hint_creation_confirm_keyboard()
        ),
    )

    await callback.answer()


@router.callback_query(
    AdminScheduleStates.confirming_hint_creation,
    F.data == "admin:create:hint:confirm",
)
async def admin_create_hint_confirm_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    data = await state.get_data()

    course_slug = data.get("course_slug")
    project_id = data.get("project_id")

    if (
        not isinstance(course_slug, str)
        or data.get("post_type") != "hint"
        or not isinstance(project_id, int)
    ):
        await callback.answer(
            "Контекст создания подсказки потерян.",
            show_alert=True,
        )
        return

    try:
        hint = await create_hint(
            course_slug=course_slug,
            project_id=project_id,
        )
    except HintCreationError as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    await state.clear()

    await _show_hint_selection(
        callback.message,
        state,
        course_slug,
        project_id,
    )

    await callback.answer(
        f"✅ Hint {hint.number} создана. "
        f"XP после публикации: "
        f"{hint.xp_after_publish}."
    )


@router.callback_query(
    AdminScheduleStates.confirming_hint_creation,
    F.data == "admin:create:hint:cancel",
)
async def admin_create_hint_cancel_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    data = await state.get_data()

    course_slug = data.get("course_slug")
    project_id = data.get("project_id")

    if (
        not isinstance(course_slug, str)
        or data.get("post_type") != "hint"
        or not isinstance(project_id, int)
    ):
        await state.clear()

        await callback.answer(
            "Контекст создания Hint потерян.",
            show_alert=True,
        )
        return

    await state.clear()

    await _show_hint_selection(
        callback.message,
        state,
        course_slug,
        project_id,
    )

    await callback.answer(
        "❌ Создание Hint отменено."
    )


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

    data = await state.get_data()

    course_slug = data.get("course_slug")

    if not isinstance(course_slug, str):
        await state.clear()

        await message.answer(
            "Контекст создания публикации потерян."
        )
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
            f"{escape(str(error))}",
            reply_markup=get_admin_add_cancel_keyboard(
                course_slug
            ),
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
        ),
        reply_markup=get_admin_add_cancel_keyboard(
            course_slug
        ),
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

    data = await state.get_data()

    course_slug = data.get("course_slug")
    post_type = data.get("post_type")
    content = data.get("content")

    if (
        not isinstance(course_slug, str)
        or post_type not in {
            "regular",
            "project",
            "hint",
        }
        or not isinstance(content, str)
    ):
        await state.clear()

        await message.answer(
            "Контекст публикации потерян.\n\n"
            "Начни создание публикации заново."
        )
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
            "<code>05.09.2026 18:30</code>",
            reply_markup=get_admin_add_cancel_keyboard(
                course_slug
            ),
        )
        return

    except NonexistentLocalTime:
        await message.answer(
            "❌ Такого местного времени "
            "не существует из-за перевода часов.\n\n"
            "Выбери другое время.",
            reply_markup=get_admin_add_cancel_keyboard(
                course_slug
            ),
        )
        return

    except AmbiguousLocalTime:
        await message.answer(
            "❌ Это время встречается дважды "
            "из-за перевода часов.\n\n"
            "Выбери другое время.",
            reply_markup=get_admin_add_cancel_keyboard(
                course_slug
            ),
        )
        return

    if scheduled_at <= datetime.now(UTC):
        await message.answer(
            "❌ Время должно быть в будущем.",
            reply_markup=get_admin_add_cancel_keyboard(
                course_slug
            ),
        )
        return

    await state.update_data(
        scheduled_at=scheduled_at.isoformat()
    )

    content_preview = (
        build_telegram_post_preview(
            content,
            max_chars=2000,
        )
    )

    await state.set_state(
        AdminScheduleStates.confirming
    )

    await message.answer(
        text=(
            "📋 <b>Проверь публикацию</b>\n\n"
            f"Тип: <b>{post_type}</b>\n"
            f"Время: <b>{value}</b>\n\n"
            "<b>Текст "
            "(предпросмотр):</b>\n\n"
            f"{content_preview}"
        ),
        reply_markup=get_schedule_confirm_keyboard(
            course_slug
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

    course_slug = data.get("course_slug")
    post_type = data.get("post_type")
    content = data.get("content")
    scheduled_at_raw = data.get(
        "scheduled_at"
    )

    if (
        not isinstance(course_slug, str)
        or post_type not in {
            "regular",
            "project",
            "hint",
        }
        or not isinstance(content, str)
        or not isinstance(
            scheduled_at_raw,
            str,
        )
    ):
        await state.clear()

        await callback.answer(
            "Контекст публикации потерян.",
            show_alert=True,
        )
        return

    try:
        scheduled_at = datetime.fromisoformat(
            scheduled_at_raw
        )

    except ValueError:
        await state.clear()

        await callback.answer(
            "Некорректное время публикации.",
            show_alert=True,
        )
        return

    try:
        post = await create_scheduled_post(
            course_slug=course_slug,
            post_type=post_type,
            content=content,
            scheduled_at=scheduled_at,
            project_id=data.get(
                "project_id"
            ),
            hint_id=data.get(
                "hint_id"
            ),
        )

    except ScheduleError as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

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