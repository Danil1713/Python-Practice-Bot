import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from app.bot.callbacks import (
    parse_callback_int_str,
    parse_callback_str,
)
from app.bot.keyboards.subscription import (
    get_payment_support_keyboard,
    get_stars_invoice_keyboard,
    get_subscription_keyboard,
)
from app.config import get_admin_username
from app.services.payment_service import (
    PaymentError,
    approve_pre_checkout,
    cancel_payment,
    create_payment,
    process_telegram_stars_payment,
)
from app.services.pricing_service import (
    get_subscription_plan,
)

logger = logging.getLogger(__name__)

router = Router()

PAYMENT_SUPPORT_TEXT = (
    "💳 <b>Поддержка по оплате</b>\n\n"
    "Если возникла проблема с оплатой, "
    "списанием Stars или активацией подписки, "
    "напиши администратору.\n\n"
    "При обращении укажи:\n"
    "• какой курс покупал;\n"
    "• примерное время оплаты;\n"
    "• что именно произошло."
)

def parse_subscription_payload(
    payload: str,
) -> int | None:
    prefix = "subscription:"

    if not payload.startswith(prefix):
        return None

    raw_payment_id = payload[
        len(prefix):
    ]

    if (
        not raw_payment_id
        or ":" in raw_payment_id
    ):
        return None

    try:
        payment_id = int(
            raw_payment_id
        )

    except ValueError:
        return None

    if payment_id <= 0:
        return None

    return payment_id

@router.callback_query(
    F.data.startswith("payment:stars:")
)
async def stars_payment_handler(
    callback: CallbackQuery,
    bot: Bot,
) -> None:
    course_slug = parse_callback_str(
        callback.data,
        "payment:stars",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    plan = get_subscription_plan(
        course_slug
    )

    if plan is None:
        await callback.answer(
            "Тариф не найден.",
            show_alert=True,
        )
        return

    try:
        payment = await create_payment(
            telegram_user_id=callback.from_user.id,
            course_slug=course_slug,
            provider="telegram_stars",
            amount=plan.stars_price,
            subscription_days=plan.days,
            currency="XTR",
        )

    except PaymentError as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    payload = f"subscription:{payment.id}"

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Подписка на Python-курс",
        description=(
            f"Доступ к {course_slug} "
            f"на {plan.days} дней."
        ),
        payload=payload,
        currency="XTR",
        prices=[
            LabeledPrice(
                label="Подписка",
                amount=plan.stars_price,
            )
        ],
        provider_token="",
        reply_markup=get_stars_invoice_keyboard(
            payment_id=payment.id,
            course_slug=course_slug,
        ),
    )

    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout_handler(
    query: PreCheckoutQuery,
) -> None:
    payload = query.invoice_payload

    payment_id = parse_subscription_payload(
        payload
    )

    if payment_id is None:
        await query.answer(
            ok=False,
            error_message=(
                "Некорректный платёж."
            ),
        )
        return

    try:
        await approve_pre_checkout(
            payment_id=payment_id,
            telegram_user_id=query.from_user.id,
            currency=query.currency,
            total_amount=query.total_amount,
        )

    except PaymentError as error:
        await query.answer(
            ok=False,
            error_message=str(error),
        )
        return

    await query.answer(
        ok=True
    )

@router.message(
    F.successful_payment
)
async def successful_payment_handler(
    message: Message,
) -> None:
    successful_payment = (
        message.successful_payment
    )

    if successful_payment is None:
        return

    payload = (
        successful_payment.invoice_payload
    )

    payment_id = parse_subscription_payload(
        payload
    )

    if payment_id is None:
        logger.error(
            "Invalid Stars successful payment "
            "payload=%r "
            "telegram_user_id=%s "
            "charge_id=%s",
            payload,
            message.from_user.id,
            (
                successful_payment
                .telegram_payment_charge_id
            ),
        )

        await message.answer(
            text=(
                "⚠️ Оплата получена, но не удалось "
                "автоматически определить платёж.\n\n"
                "Stars уже могли быть списаны. "
                "Обратись в поддержку, чтобы "
                "проверить платёж и активировать "
                "подписку."
            ),
            reply_markup=(
                get_payment_support_keyboard()
            ),
        )
        return

    try:
        processed = (
            await process_telegram_stars_payment(
                payment_id=payment_id,
                telegram_user_id=(
                    message.from_user.id
                ),
                telegram_payment_charge_id=(
                    successful_payment
                    .telegram_payment_charge_id
                ),
                currency=(
                    successful_payment.currency
                ),
                total_amount=(
                    successful_payment.total_amount
                ),
            )
        )

    except PaymentError as error:
        logger.error(
            "Could not finalize Stars payment "
            "payment_id=%s "
            "telegram_user_id=%s "
            "charge_id=%s "
            "error=%s",
            payment_id,
            message.from_user.id,
            (
                successful_payment
                .telegram_payment_charge_id
            ),
            error,
        )

        await message.answer(
            text=(
                "⚠️ Оплата получена, но возникла "
                "ошибка при активации подписки.\n\n"
                "Stars уже могли быть списаны. "
                "Обратись в поддержку — платёж "
                "нужно проверить."
            ),
            reply_markup=(
                get_payment_support_keyboard()
            ),
        )
        return

    await message.answer(
        text=(
            "✅ <b>Оплата прошла успешно!</b>\n\n"
            "Подписка активирована "
            f"на {processed.subscription_days} дней."
        ),
        reply_markup=get_subscription_keyboard(
            course_slug=processed.course_slug,
            can_pay=False,
        ),
    )

@router.callback_query(
    F.data.startswith("payment:cancel:")
)
async def cancel_stars_payment_handler(
    callback: CallbackQuery,
) -> None:
    parsed = parse_callback_int_str(
        callback.data,
        "payment:cancel",
    )

    if parsed is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    payment_id, course_slug = parsed

    try:
        cancelled = await cancel_payment(
            payment_id=payment_id,
            telegram_user_id=callback.from_user.id,
            course_slug=course_slug,
        )

    except PaymentError as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    if not cancelled:
        await callback.answer(
            "Этот платёж уже обработан.",
            show_alert=True,
        )
        return

    await callback.message.delete()

    plan = get_subscription_plan(
        course_slug
    )

    await callback.message.answer(
        text=(
            "❌ <b>Оплата отменена.</b>\n\n"
            "Подписка не была изменена."
        ),
        reply_markup=get_subscription_keyboard(
            course_slug=course_slug,
            can_pay=plan is not None,
            stars_price=(
                plan.stars_price
                if plan is not None
                else None
            ),
            admin_username=get_admin_username(),
        ),
    )

async def show_payment_support(
    message: Message,
) -> None:
    await message.answer(
        text=PAYMENT_SUPPORT_TEXT,
        reply_markup=get_payment_support_keyboard(),
    )

@router.message(Command("paysupport"))
async def payment_support_handler(
    message: Message,
) -> None:
    await show_payment_support(message)

@router.callback_query(
    F.data.startswith("payment:support:")
)
async def payment_support_callback_handler(
    callback: CallbackQuery,
) -> None:
    course_slug = parse_callback_str(
        callback.data,
        "payment:support",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        text=PAYMENT_SUPPORT_TEXT,
        reply_markup=get_payment_support_keyboard(course_slug),
    )

    await callback.answer()