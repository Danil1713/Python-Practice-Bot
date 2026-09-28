from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.callbacks import (
    parse_callback_str,
)
from app.bot.handlers.course_context import (
    check_current_course,
)
from app.bot.keyboards.progress import (
    get_progress_keyboard,
)
from app.services.progress_service import (
    get_course_progress,
)
from app.utils.telegram_text import (
    split_telegram_lines,
)

router = Router()


STATUS_ICONS = {
    "completed": "✅",
    "available": "🟡",
    "locked": "🔒",
}


@router.callback_query(
    F.data.startswith("menu:progress:")
)
async def progress_handler(
    callback: CallbackQuery,
) -> None:
    course_slug = parse_callback_str(
        callback.data,
        "menu:progress",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    if not await check_current_course(
            callback,
            course_slug,
    ):
        return

    view = await get_course_progress(
        telegram_user_id=callback.from_user.id,
        course_slug=course_slug,
    )

    if view is None:
        await callback.answer(
            "Не удалось получить прогресс.",
            show_alert=True,
        )
        return

    course_title = escape(
        view.course_title
    )

    lines = [
        f"<b>📊 Прогресс — "
        f"{course_title}</b>",
        "",
        (
            f"Выполнено проектов: "
            f"<b>{view.completed_count} "
            f"/ {view.total_count}</b>"
        ),
        (
            f"Прогресс: "
            f"<b>{view.percent}%</b>"
        ),
        "",
    ]

    for project in view.projects:
        icon = STATUS_ICONS.get(
            project.status,
            "❔",
        )

        lines.append(
            f"{icon} Project "
            f"{project.number} — "
            f"{escape(project.title)}"
        )

    chunks = split_telegram_lines(
        lines
    )

    if not chunks:
        await callback.answer(
            "Не удалось сформировать прогресс.",
            show_alert=True,
        )
        return

    if len(chunks) == 1:
        await callback.message.edit_text(
            text=chunks[0],
            reply_markup=get_progress_keyboard(
                view.course_slug
            ),
        )

    else:
        await callback.message.edit_text(
            text=chunks[0]
        )

        for chunk in chunks[1:-1]:
            await callback.message.answer(
                chunk
            )

        await callback.message.answer(
            chunks[-1],
            reply_markup=get_progress_keyboard(
                view.course_slug
            ),
        )

    await callback.answer()