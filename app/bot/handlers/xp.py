from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.callbacks import (
    parse_callback_str,
)
from app.bot.handlers.course_context import (
    check_current_course,
)
from app.bot.keyboards.xp import (
    get_xp_keyboard,
)
from app.services.xp_service import (
    get_course_xp,
)

router = Router()


@router.callback_query(F.data.startswith("menu:xp:"))
async def xp_handler(
    callback: CallbackQuery,
) -> None:
    course_slug = parse_callback_str(
        callback.data,
        "menu:xp",
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

    view = await get_course_xp(
        telegram_user_id=callback.from_user.id,
        course_slug=course_slug,
    )

    if view is None:
        await callback.answer(
            "Не удалось получить XP.",
            show_alert=True,
        )
        return

    course_title = escape(view.course_title)

    lines = [
        f"<b>⭐ XP — {course_title}</b>",
        "",
        f"Всего XP: <b>{view.total_xp}</b>",
    ]

    if view.history:
        lines.extend(
            [
                "",
                "<b>Последние начисления:</b>",
            ]
        )

        for item in view.history:
            if item.project_number is not None:
                title = escape(item.project_title or "")

                lines.append(
                    f"+{item.amount} XP — Project {item.project_number} {title}"
                )
            else:
                lines.append(f"+{item.amount} XP — {escape(item.reason)}")

    else:
        lines.extend(
            [
                "",
                "Начислений пока нет.",
            ]
        )

    await callback.message.edit_text(
        text="\n".join(lines),
        reply_markup=get_xp_keyboard(view.course_slug),
    )

    await callback.answer()
