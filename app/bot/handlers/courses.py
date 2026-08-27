from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.courses import (
    get_courses_keyboard,
)
from app.bot.keyboards.main_menu import (
    get_main_menu_keyboard,
)
from app.services.course_service import (
    get_active_courses,
    get_course_by_slug,
)
from app.services.subscription_service import (
    has_active_subscription,
)


router = Router()


@router.callback_query(
    F.data.startswith("course:")
)
async def select_course_handler(
    callback: CallbackQuery,
) -> None:
    course_slug = callback.data.split(":")[1]

    course = await get_course_by_slug(
        course_slug
    )

    if course is None:
        await callback.answer(
            "Уровень не найден.",
            show_alert=True,
        )
        return

    has_subscription = (
        await has_active_subscription(
            telegram_user_id=callback.from_user.id,
            course_slug=course.slug,
        )
    )

    if has_subscription:
        text = (
            f"<b>{course.title}</b>\n\n"
            "Выбери нужный раздел:"
        )

    else:
        text = (
            f"<b>{course.title}</b>\n\n"
            "⚠️ У тебя пока нет активной "
            "подписки на этот уровень.\n\n"
            "Ты можешь посмотреть интерфейс "
            "курса, но функции, требующие "
            "активной подписки, "
            "будут недоступны.\n\n"
            "Выбери нужный раздел:"
        )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_main_menu_keyboard(
            course.slug
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data == "nav:courses"
)
async def back_to_courses_handler(
    callback: CallbackQuery,
) -> None:
    courses = await get_active_courses()

    await callback.message.edit_text(
        text=(
            "Выбери уровень, "
            "с которым хочешь работать:"
        ),
        reply_markup=get_courses_keyboard(
            courses
        ),
    )

    await callback.answer()