from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.subscription import (
    get_subscription_keyboard, format_subscription_datetime,
)
from app.config import get_app_timezone
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
    course_slug = callback.data.split(":")[2]

    view = await get_subscription_view(
        telegram_user_id=callback.from_user.id,
        course_slug=course_slug,
    )

    if view is None:
        await callback.answer(
            "Не удалось получить подписку.",
            show_alert=True,
        )
        return

    if not view.requires_subscription:
        text = (
            f"🎁 <b>{view.course_title}</b>\n\n"
            "Этот уровень доступен бесплатно."
        )

    elif view.status == "active":
        text = (
            "💎 <b>Подписка активна</b>\n\n"
            f"Курс: <b>{view.course_title}</b>\n"
            f"Действует до: <b>"
            f"{format_subscription_datetime(view.ends_at)}"
            f"</b>"
        )

    elif view.status == "expired":
        text = (
            "⌛ <b>Подписка закончилась</b>\n\n"
            f"Курс: <b>{view.course_title}</b>\n"
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
            f"Курс: <b>{view.course_title}</b>\n\n"
            "Для доступа к материалам "
            "нужна активная подписка."
        )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_subscription_keyboard(
            course_slug
        ),
    )

    await callback.answer()