from datetime import UTC, datetime
from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import (
    parse_callback_int_str,
    parse_callback_str,
)
from app.bot.handlers.admin_common import (
    check_admin,
    format_admin_datetime,
)
from app.bot.keyboards.admin import (
    get_admin_input_cancel_keyboard,
    get_schedule_keyboard,
    get_scheduled_post_keyboard,
)
from app.bot.states.admin import (
    AdminScheduleStates,
)
from app.config import get_app_timezone
from app.services.admin_service import (
    is_admin,
)
from app.services.schedule_service import (
    ScheduledPostNotEditable,
    ScheduledPostNotFound,
    ScheduleError,
    cancel_scheduled_post,
    get_course_schedule,
    get_scheduled_post_detail,
    publish_post_now,
    reschedule_post,
)
from app.utils.datetime_utils import (
    AmbiguousLocalTime,
    InvalidDateTimeFormat,
    NonexistentLocalTime,
    parse_local_datetime_to_utc,
)

router = Router()

@router.callback_query(
    F.data.startswith("admin:schedule:")
)
async def admin_schedule_handler(
    callback: CallbackQuery,
) -> None:
    if not await check_admin(callback):
        return

    course_slug = parse_callback_str(
        callback.data,
        "admin:schedule",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

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

    parsed = parse_callback_int_str(
        callback.data,
        "admin:post",
    )

    if parsed is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    post_id, course_slug = parsed

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

    parsed = parse_callback_int_str(
        callback.data,
        "admin:publish",
    )

    if parsed is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    post_id, course_slug = parsed

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

    except ScheduleError as error:
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

    parsed = parse_callback_int_str(
        callback.data,
        "admin:cancel",
    )

    if parsed is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    post_id, course_slug = parsed

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

    parsed = parse_callback_int_str(
        callback.data,
        "admin:reschedule",
    )

    if parsed is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    post_id, course_slug = parsed

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
            f"Часовой пояс: "
            f"<code>{escape(get_app_timezone())}</code>"
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

    data = await state.get_data()

    post_id = data.get("post_id")
    course_slug = data.get("course_slug")

    if (
        not isinstance(post_id, int)
        or not isinstance(course_slug, str)
    ):
        await state.clear()

        await message.answer(
            "Контекст переноса публикации потерян."
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
            "Используй:\n"
            "<code>05.09.2026 18:30</code>",
            reply_markup=get_admin_input_cancel_keyboard(
                post_id=post_id,
                course_slug=course_slug,
            ),
        )
        return

    except NonexistentLocalTime:
        await message.answer(
            "❌ Такого местного времени "
            "не существует из-за перевода часов.\n\n"
            "Выбери другое время.",
            reply_markup=get_admin_input_cancel_keyboard(
                post_id=post_id,
                course_slug=course_slug,
            ),
        )
        return

    except AmbiguousLocalTime:
        await message.answer(
            "❌ Это время встречается дважды "
            "из-за перевода часов.\n\n"
            "Выбери другое время.",
            reply_markup=get_admin_input_cancel_keyboard(
                post_id=post_id,
                course_slug=course_slug,
            ),
        )
        return

    if scheduled_at <= datetime.now(UTC):
        await message.answer(
            "❌ Время должно быть в будущем.",
            reply_markup=get_admin_input_cancel_keyboard(
                post_id=post_id,
                course_slug=course_slug,
            ),
        )
        return

    try:
        await reschedule_post(
            post_id=post_id,
            scheduled_at=scheduled_at,
        )

    except ScheduleError as error:
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
