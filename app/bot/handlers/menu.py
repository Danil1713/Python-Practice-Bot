from aiogram import F, Router
from aiogram.types import CallbackQuery
from html import escape

from app.bot.keyboards.main_menu import (
    get_back_to_menu_keyboard,
    get_main_menu_keyboard,
)
from app.services.course_service import (
    get_course_by_slug,
)
from app.services.subscription_service import (
    has_active_subscription,
)
from app.services.admin_service import (
    is_admin,
)
from app.bot.callbacks import (
    parse_callback_str,
)


router = Router()


@router.callback_query(
    F.data.startswith(
        "menu:about:"
    )
)
async def menu_section_handler(
    callback: CallbackQuery,
) -> None:
    course_slug = parse_callback_str(
        callback.data,
        "menu:about",
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

    course_title = escape(
        course.title
    )

    course_description = escape(
        course.description or ""
    )

    text = (
        f"<b>ℹ️ {course_title}</b>\n\n"
        f"{course_description or ''}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_to_menu_keyboard(
            course.slug
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("nav:menu:")
)
async def back_to_menu_handler(
    callback: CallbackQuery,
) -> None:
    course_slug = parse_callback_str(
        callback.data,
        "nav:menu",
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

    course_title = escape(
        course.title
    )

    await callback.message.edit_text(
        text=(
            f"<b>{course_title}</b>\n\n"
            "Выбери нужный раздел:"
        ),
        reply_markup=get_main_menu_keyboard(
            course_slug=course.slug,
            requires_subscription=course.requires_subscription,
            is_admin_user=is_admin(
                callback.from_user.id
            ),
        ),
    )

    await callback.answer()