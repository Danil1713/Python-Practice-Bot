from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from app.bot.keyboards.subscription import get_stars_invoice_keyboard, get_subscription_keyboard, \
    get_payment_support_keyboard
from app.config import get_admin_username
from app.services.payment_service import (
    PaymentError,
    create_payment,
    get_payment_checkout_view,
    process_telegram_stars_payment, cancel_payment,
)
from app.services.pricing_service import (
    get_subscription_plan,
)


router = Router()

@router.callback_query(
    F.data.startswith("payment:stars:")
)
async def stars_payment_handler(
    callback: CallbackQuery,
    bot: Bot,
) -> None:
    course_slug = callback.data.split(":")[2]

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

    if not payload.startswith(
        "subscription:"
    ):
        await query.answer(
            ok=False,
            error_message=(
                "Некорректный платёж."
            ),
        )
        return

    try:
        payment_id = int(
            payload.split(":")[1]
        )
    except (ValueError, IndexError):
        await query.answer(
            ok=False,
            error_message=(
                "Некорректный платёж."
            ),
        )
        return

    payment = await get_payment_checkout_view(
        payment_id
    )

    if payment is None:
        await query.answer(
            ok=False,
            error_message=(
                "Платёж не найден."
            ),
        )
        return

    if payment.status != "pending":
        await query.answer(
            ok=False,
            error_message=(
                "Этот платёж уже обработан."
            ),
        )
        return

    if (
        payment.telegram_user_id
        != query.from_user.id
    ):
        await query.answer(
            ok=False,
            error_message=(
                "Этот платёж принадлежит "
                "другому пользователю."
            ),
        )
        return

    if query.currency != payment.currency:
        await query.answer(
            ok=False,
            error_message=(
                "Некорректная валюта."
            ),
        )
        return

    if query.total_amount != payment.amount:
        await query.answer(
            ok=False,
            error_message=(
                "Некорректная сумма."
            ),
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

    payload = successful_payment.invoice_payload

    if not payload.startswith(
        "subscription:"
    ):
        return

    try:
        payment_id = int(
            payload.split(":")[1]
        )
    except (ValueError, IndexError):
        return

    try:
        processed = (
            await process_telegram_stars_payment(
                payment_id=payment_id,
                telegram_user_id=message.from_user.id,
                telegram_payment_charge_id=(
                    successful_payment
                    .telegram_payment_charge_id
                ),
                currency=successful_payment.currency,
                total_amount=(
                    successful_payment.total_amount
                ),
            )
        )

    except PaymentError:
        await message.answer(
            "⚠️ Оплата получена, но возникла "
            "ошибка при активации подписки.\n\n"
            "Обратись к администратору."
        )
        return

    if not processed:
        return

    await message.answer(
        text=(
            "✅ <b>Оплата прошла успешно!</b>\n\n"
            "Подписка активирована "
            "на 30 дней."
        )
    )

@router.callback_query(
    F.data.startswith("payment:cancel:")
)
async def cancel_stars_payment_handler(
    callback: CallbackQuery,
) -> None:
    parts = callback.data.split(":")

    payment_id = int(parts[2])
    course_slug = parts[3]

    try:
        cancelled = await cancel_payment(
            payment_id=payment_id,
            telegram_user_id=callback.from_user.id,
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
        text=(
            "💳 <b>Поддержка по оплате</b>\n\n"
            "Если возникла проблема с оплатой, "
            "списанием Stars или активацией подписки, "
            "напиши администратору.\n\n"
            "При обращении укажи:\n"
            "• какой курс покупал;\n"
            "• примерное время оплаты;\n"
            "• что именно произошло."
        ),
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
    course_slug = callback.data.split(":")[2]

    await callback.message.edit_text(
        text=(
            "💳 <b>Поддержка по оплате</b>\n\n"
            "Если возникла проблема с оплатой, "
            "списанием Stars или активацией подписки, "
            "напиши администратору.\n\n"
            "При обращении укажи:\n"
            "• какой курс покупал;\n"
            "• примерное время оплаты;\n"
            "• что именно произошло."
        ),
        reply_markup=get_payment_support_keyboard(course_slug),
    )

    await callback.answer()