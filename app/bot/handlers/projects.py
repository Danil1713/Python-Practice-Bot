from html import escape

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.bot.callbacks import (
    parse_callback_int,
    parse_callback_str,
)
from app.bot.keyboards.projects import (
    get_projects_keyboard,
)
from app.bot.views.project_card import (
    render_project_card,
)
from app.services.project_service import (
    get_course_projects,
    get_project_card,
)
from app.services.subscription_service import (
    has_active_subscription,
)
from app.services.telegram_link_service import (
    build_channel_message_url,
)

router = Router()


@router.callback_query(
    F.data.startswith("menu:projects:")
)
async def projects_list_handler(
    callback: CallbackQuery,
) -> None:
    course_slug = parse_callback_str(
        callback.data,
        "menu:projects",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    view = await get_course_projects(
        telegram_user_id=callback.from_user.id,
        course_slug=course_slug,
    )

    if view is None:
        await callback.answer(
            "Уровень не найден.",
            show_alert=True,
        )
        return

    course_title = escape(
        view.course_title
    )

    text = (
        f"<b>📚 Проекты — "
        f"{course_title}</b>\n\n"
        "Проекты открываются только "
        "после их публикации в канале.\n\n"
        "🔒 — ещё не опубликован\n"
        "🟡 — доступен\n"
        "✅ — выполнен"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_projects_keyboard(
            projects=view.projects,
            course_slug=view.course_slug,
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("project:open:")
)
async def project_card_handler(
    callback: CallbackQuery,
) -> None:
    project_id = parse_callback_int(
        callback.data,
        "project:open",
    )

    if project_id is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    project = await get_project_card(
        telegram_user_id=callback.from_user.id,
        project_id=project_id,
    )

    if project is None:
        await callback.answer(
            "Проект не найден.",
            show_alert=True,
        )
        return

    if project.status == "locked":
        await callback.answer(
            "🔒 Проект ещё не опубликован "
            "в канале.",
            show_alert=True,
        )
        return

    active = await has_active_subscription(
        telegram_user_id=callback.from_user.id,
        course_slug=project.course_slug,
    )

    text, keyboard = render_project_card(
        project,
        active_subscription=active,
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("project:task:")
)
async def project_task_handler(
    callback: CallbackQuery,
) -> None:
    project_id = parse_callback_int(
        callback.data,
        "project:task",
    )

    if project_id is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    project = await get_project_card(
        telegram_user_id=callback.from_user.id,
        project_id=project_id,
    )

    if project is None:
        await callback.answer(
            "Проект не найден.",
            show_alert=True,
        )
        return

    active = await has_active_subscription(
        telegram_user_id=callback.from_user.id,
        course_slug=project.course_slug,
    )

    if not active:
        await callback.answer(
            "🔒 Задание доступно только "
            "при активной подписке.",
            show_alert=True,
        )
        return

    if project.telegram_message_id is None:
        await callback.answer(
            "Пост проекта пока не привязан "
            "к Telegram.",
            show_alert=True,
        )
        return

    if project.telegram_channel_id is None:
        await callback.answer(
            "Telegram-канал курса "
            "не настроен.",
            show_alert=True,
        )
        return

    post_url = build_channel_message_url(
        channel_id=project.telegram_channel_id,
        message_id=project.telegram_message_id,
    )

    if post_url is None:
        await callback.answer(
            "Не удалось сформировать "
            "ссылку на публикацию.",
            show_alert=True,
        )
        return

    project_title = escape(
        project.title
    )

    await callback.message.answer(
        text=(
            f"📖 <b>Project "
            f"{project.number} — "
            f"{project_title}</b>\n\n"
            "Открой опубликованное задание "
            "по кнопке ниже."
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📖 Открыть задание",
                        url=post_url,
                    )
                ]
            ]
        ),
    )

    await callback.answer()