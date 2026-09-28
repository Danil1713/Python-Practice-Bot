from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.callbacks import (
    parse_callback_str,
)
from app.bot.keyboards.courses import (
    get_courses_keyboard,
)
from app.bot.keyboards.main_menu import (
    get_main_menu_keyboard,
)
from app.services.admin_service import (
    is_admin,
)
from app.services.course_service import (
    get_active_courses,
    get_course_by_slug,
)
from app.services.subscription_service import (
    has_active_subscription,
)
from app.services.user_service import (
    clear_current_course,
    get_current_course_slug,
    set_current_course,
)

router = Router()


@router.callback_query(
    F.data.startswith("course:")
)
async def select_course_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    course_slug = parse_callback_str(
        callback.data,
        "course",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    course = await get_course_by_slug(
        course_slug
    )

    if course is None:
        await callback.answer(
            "Уровень не найден.",
            show_alert=True,
        )
        return

    current_course_slug = (
        await get_current_course_slug(
            callback.from_user.id
        )
    )

    if (
            current_course_slug is not None
            and current_course_slug != course.slug
    ):
        await callback.answer(
            "Сначала нажми "
            "«Сменить уровень».",
            show_alert=True,
        )
        return

    if current_course_slug is None:
        selected = await set_current_course(
            telegram_id=callback.from_user.id,
            course_slug=course.slug,
        )

        if not selected:
            await callback.answer(
                "Не удалось выбрать уровень. "
                "Попробуй /start.",
                show_alert=True,
            )
            return

    await state.clear()

    course_title = escape(
        course.title
    )

    has_subscription = (
        await has_active_subscription(
            telegram_user_id=callback.from_user.id,
            course_slug=course.slug,
        )
    )

    if has_subscription:
        text = (
            f"<b>{course_title}</b>\n\n"
            "Выбери нужный раздел:"
        )

    else:
        text = (
            f"<b>{course_title}</b>\n\n"
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
            course_slug=course.slug,
            requires_subscription=course.requires_subscription,
            is_admin_user=is_admin(
                callback.from_user.id
            ),
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data == "nav:courses"
)
async def back_to_courses_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    await clear_current_course(
        callback.from_user.id
    )

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