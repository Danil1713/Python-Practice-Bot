from aiogram import F, Router
from aiogram.types import CallbackQuery

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


router = Router()


@router.callback_query(
    F.data.regexp(
        r"^menu:(subscription|about):"
    )
)
async def menu_section_handler(
    callback: CallbackQuery,
) -> None:
    _, section, course_slug = (
        callback.data.split(":")
    )

    course = await get_course_by_slug(
        course_slug
    )

    if course is None:
        await callback.answer(
            "Уровень не найден.",
            show_alert=True,
        )
        return

    if section == "subscription":
        active = (
            await has_active_subscription(
                telegram_user_id=callback.from_user.id,
                course_slug=course.slug,
            )
        )

        if active:
            text = (
                f"<b>💳 Подписка — "
                f"{course.title}</b>\n\n"
                "✅ Подписка активна."
            )
        else:
            text = (
                f"<b>💳 Подписка — "
                f"{course.title}</b>\n\n"
                "❌ Активной подписки "
                "пока нет."
            )

    elif section == "about":
        text = (
            f"<b>ℹ️ {course.title}</b>\n\n"
            f"{course.description or ''}"
        )

    else:
        text = "Неизвестный раздел."

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
    course_slug = callback.data.split(":")[2]

    course = await get_course_by_slug(
        course_slug
    )

    if course is None:
        await callback.answer(
            "Уровень не найден.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        text=(
            f"<b>{course.title}</b>\n\n"
            "Выбери нужный раздел:"
        ),
        reply_markup=get_main_menu_keyboard(
            course_slug=course.slug,
            requires_subscription=course.requires_subscription,
        ),
    )

    await callback.answer()