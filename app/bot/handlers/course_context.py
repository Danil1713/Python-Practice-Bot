from aiogram.types import CallbackQuery

from app.services.user_service import (
    is_current_course,
)


async def check_current_course(
    callback: CallbackQuery,
    course_slug: str,
) -> bool:
    valid = await is_current_course(
        telegram_id=callback.from_user.id,
        course_slug=course_slug,
    )

    if valid:
        return True

    await callback.answer(
        "Этот уровень сейчас не выбран. Нажми «Сменить уровень» или используй /start.",
        show_alert=True,
    )

    return False
