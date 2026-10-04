from aiogram.types import CallbackQuery, Message

from app.services.user_service import (
    is_current_course,
)


async def check_current_course(
    event: CallbackQuery | Message,
    course_slug: str,
) -> bool:
    if event.from_user is None:
        return False

    valid = await is_current_course(
        telegram_id=event.from_user.id,
        course_slug=course_slug,
    )

    if valid:
        return True

    text = (
        "Этот уровень сейчас не выбран. Нажми «Сменить уровень» или используй /start."
    )

    if isinstance(event, CallbackQuery):
        await event.answer(
            text,
            show_alert=True,
        )

    else:
        await event.answer(text)

    return False
