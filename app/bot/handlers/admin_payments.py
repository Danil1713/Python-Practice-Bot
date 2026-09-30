import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.callbacks import (
    parse_callback_int_str,
    parse_callback_str,
)
from app.bot.handlers.admin_common import (
    check_admin,
)
from app.bot.keyboards.admin import (
    get_review_payment_keyboard,
    get_review_payments_keyboard,
)
from app.bot.keyboards.subscription import (
    get_subscription_keyboard,
)
from app.services.course_service import (
    get_course_by_slug,
)
from app.services.payment_service import (
    PaymentError,
    get_review_payment_detail,
    get_review_payments_for_course,
    retry_payment_activation,
)

logger = logging.getLogger(__name__)

router = Router()


def build_review_payments_text(
    *,
    course_title: str,
    payments: list,
) -> str:
    lines = [
        "💳 <b>Платежи на проверке</b>",
        "",
        f"Курс: <b>{escape(course_title)}</b>",
        "",
    ]

    if not payments:
        lines.append(
            "✅ Платежей, требующих проверки, нет."
        )

        return "\n".join(lines)

    for payment in payments:
        if payment.username:
            user_label = (
                f"@{payment.username}"
            )
        else:
            user_label = str(
                payment.telegram_user_id
            )

        lines.append(
            (
                f"⚠️ <b>#{payment.id}</b> — "
                f"{escape(user_label)} — "
                f"{payment.amount} "
                f"{escape(payment.currency)}"
            )
        )

    return "\n".join(lines)


@router.callback_query(
    F.data.startswith(
        "admin:payreview:"
    )
)
async def admin_review_payments_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await check_admin(callback):
        return

    await state.clear()

    course_slug = parse_callback_str(
        callback.data,
        "admin:payreview",
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
            "Курс не найден.",
            show_alert=True,
        )
        return

    try:
        payments = (
            await get_review_payments_for_course(
                course_slug
            )
        )

    except PaymentError as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        text=build_review_payments_text(
            course_title=course.title,
            payments=payments,
        ),
        reply_markup=get_review_payments_keyboard(
            course_slug,
            payments,
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith(
        "admin:payreview-item:"
    )
)
async def admin_review_payment_handler(
    callback: CallbackQuery,
) -> None:
    if not await check_admin(callback):
        return

    parsed = parse_callback_int_str(
        callback.data,
        "admin:payreview-item",
    )

    if parsed is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    payment_id, course_slug = parsed

    payment = await get_review_payment_detail(
        payment_id=payment_id,
        course_slug=course_slug,
    )

    if payment is None:
        await callback.answer(
            "Платёж уже обработан "
            "или не найден.",
            show_alert=True,
        )
        return

    if payment.username:
        user_label = (
            f"@{payment.username}"
        )
    else:
        user_label = "—"

    error_text = (
        payment.error_message
        or "Ошибка не указана."
    )

    if len(error_text) > 1000:
        error_text = (
            error_text[:1000]
            + "..."
        )

    charge_id = (
        payment.external_payment_id
        or "не сохранён"
    )

    await callback.message.edit_text(
        text=(
            f"⚠️ <b>Платёж #{payment.id}</b>\n\n"
            f"Курс: <b>"
            f"{escape(payment.course_title)}"
            f"</b>\n"
            f"Telegram ID: <code>"
            f"{payment.telegram_user_id}"
            f"</code>\n"
            f"Username: <b>"
            f"{escape(user_label)}"
            f"</b>\n\n"
            f"Сумма: <b>"
            f"{payment.amount} "
            f"{escape(payment.currency)}"
            f"</b>\n"
            f"Подписка: <b>"
            f"{payment.subscription_days} дней"
            f"</b>\n\n"
            f"Charge ID:\n"
            f"<code>{escape(charge_id)}</code>\n\n"
            f"<b>Ошибка:</b>\n"
            f"<code>{escape(error_text)}</code>"
        ),
        reply_markup=get_review_payment_keyboard(
            payment_id=payment.id,
            course_slug=course_slug,
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith(
        "admin:payreview-retry:"
    )
)
async def admin_review_payment_retry_handler(
    callback: CallbackQuery,
    bot: Bot,
) -> None:
    if not await check_admin(callback):
        return

    parsed = parse_callback_int_str(
        callback.data,
        "admin:payreview-retry",
    )

    if parsed is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    payment_id, course_slug = parsed

    payment = await get_review_payment_detail(
        payment_id=payment_id,
        course_slug=course_slug,
    )

    if payment is None:
        await callback.answer(
            "Платёж уже обработан "
            "или не найден.",
            show_alert=True,
        )
        return

    try:
        activated = await retry_payment_activation(
            payment_id=payment_id
        )

    except PaymentError as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    if not activated:
        await callback.answer(
            "Платёж уже был обработан.",
            show_alert=True,
        )
        return

    notification_sent = True

    try:
        await bot.send_message(
            chat_id=payment.telegram_user_id,
            text=(
                "✅ <b>Подписка активирована.</b>\n\n"
                "Проблема с оплатой исправлена.\n"
                "Доступ к курсу теперь активен."
            ),
            reply_markup=get_subscription_keyboard(
                course_slug=payment.course_slug,
                can_pay=False,
                can_open_channel=True,
            ),
        )

    except Exception:
        notification_sent = False

        logger.exception(
            "Could not notify user after "
            "payment review activation "
            "payment_id=%s "
            "telegram_user_id=%s",
            payment.id,
            payment.telegram_user_id,
        )

    course = await get_course_by_slug(
        course_slug
    )

    if course is None:
        await callback.message.edit_text(
            "✅ Подписка активирована."
        )

        await callback.answer()
        return

    payments = (
        await get_review_payments_for_course(
            course_slug
        )
    )

    await callback.message.edit_text(
        text=(
            "✅ <b>Подписка активирована.</b>\n\n"
            f"Платёж: <b>#{payment.id}</b>\n"
            f"Пользователь: <code>"
            f"{payment.telegram_user_id}"
            f"</code>\n\n"
            f"Осталось платежей "
            f"на проверке: <b>"
            f"{len(payments)}</b>"
        ),
        reply_markup=get_review_payments_keyboard(
            course_slug,
            payments,
        ),
    )

    if notification_sent:
        await callback.answer(
            "Подписка активирована."
        )

    else:
        await callback.answer(
            "Подписка активирована, "
            "но уведомление пользователю "
            "не отправилось.",
            show_alert=True,
        )