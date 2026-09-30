from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.callbacks import (
    parse_callback_str,
)
from app.bot.handlers.admin_common import (
    check_admin,
)
from app.bot.handlers.admin_payments import (
    router as admin_payments_router,
)
from app.bot.handlers.admin_post_creation import (
    router as admin_post_creation_router,
)
from app.bot.handlers.admin_posts import (
    router as admin_posts_router,
)
from app.bot.handlers.admin_subscriptions import (
    router as admin_subscriptions_router,
)
from app.bot.keyboards.admin import (
    get_admin_menu_keyboard,
)
from app.services.course_service import get_course_by_slug

router = Router()


@router.callback_query(F.data.startswith("admin:menu:"))
async def admin_menu_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    await state.clear()

    course_slug = parse_callback_str(
        callback.data,
        "admin:menu",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    course = await get_course_by_slug(course_slug)

    if course is None:
        await callback.answer(
            "Курс не найден.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        text=(
            "⚙️ <b>Админ-панель</b>\n\n"
            f"Курс: <b>{escape(course_slug)}</b>\n\n"
            "Здесь можно управлять "
            "публикациями курса."
        ),
        reply_markup=get_admin_menu_keyboard(course_slug, course.requires_subscription),
    )

    await callback.answer()


router.include_router(admin_post_creation_router)

router.include_router(admin_posts_router)

router.include_router(admin_subscriptions_router)

router.include_router(admin_payments_router)
