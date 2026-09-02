from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.progress import (
    get_progress_keyboard,
)
from app.services.progress_service import (
    get_course_progress,
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
    course_slug = callback.data.split(":")[2]

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

    lines = [
        f"<b>📊 Прогресс — "
        f"{view.course_title}</b>",
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
            f"{project.title}"
        )

    await callback.message.edit_text(
        text="\n".join(lines),
        reply_markup=get_progress_keyboard(
            view.course_slug
        ),
    )

    await callback.answer()