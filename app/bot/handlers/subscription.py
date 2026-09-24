from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.callbacks import (
    parse_callback_str,
)
from app.bot.keyboards.subscription import (
    format_subscription_datetime,
    get_subscription_keyboard,
)
from app.config import get_admin_username
from app.services.pricing_service import get_subscription_plan
from app.services.subscription_service import (
    get_subscription_view,
)

router = Router()

@router.callback_query(
    F.data.startswith("menu:subscription:")
)
async def subscription_handler(
    callback: CallbackQuery,
) -> None:
    course_slug = parse_callback_str(
        callback.data,
        "menu:subscription",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    view = await get_subscription_view(
        telegram_user_id=callback.from_user.id,
        course_slug=course_slug,
    )

    course_title = escape(
        view.course_title
    )

    plan = get_subscription_plan(
        course_slug
    )

    if view is None:
        await callback.answer(
            "Не удалось получить подписку.",
            show_alert=True,
        )
        return

    if not view.requires_subscription:
        text = (
            f"🎁 <b>{course_title}</b>\n\n"
            "Этот уровень доступен бесплатно."
        )

    elif view.status == "active":
        text = (
            "💎 <b>Подписка активна</b>\n\n"
            f"Курс: <b>{course_title}</b>\n"
            f"Действует до: <b>"
            f"{format_subscription_datetime(view.ends_at)}"
            f"</b>"
        )

    elif view.status == "expired":
        text = (
            "⌛ <b>Подписка закончилась</b>\n\n"
            f"Курс: <b>{course_title}</b>\n"
        )

        if view.ends_at is not None:
            text += (
                f"Доступ закончился: <b>"
                f"{format_subscription_datetime(view.ends_at)}"
                f"</b>\n\n"
            )

        text += (
            "Прогресс, XP и история попыток "
            "сохранены."
        )

    else:
        text = (
            "🔒 <b>Подписка не активна</b>\n\n"
            f"Курс: <b>{course_title}</b>\n\n"
            "Для доступа к материалам "
            "нужна активная подписка."
        )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_subscription_keyboard(
            course_slug=course_slug,
            can_pay=(
                    view.requires_subscription
                    and plan is not None
            ),
            stars_price=(
                plan.stars_price
                if plan is not None
                else None
            ),
            admin_username=get_admin_username(),
        ),
    )

    await callback.answer()