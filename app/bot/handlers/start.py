from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.courses import (
    get_courses_keyboard,
)
from app.services.course_service import (
    get_active_courses,
)
from app.services.user_service import (
    register_or_update_user,
)

router = Router()


@router.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
) -> None:
    telegram_user = message.from_user

    if telegram_user is None:
        return

    await state.clear()

    await register_or_update_user(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
    )

    courses = await get_active_courses()

    await message.answer(
        text=(
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Выбери уровень, "
            "с которым хочешь работать:"
        ),
        reply_markup=get_courses_keyboard(
            courses
        ),
    )