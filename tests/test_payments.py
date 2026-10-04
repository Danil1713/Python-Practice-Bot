import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.bot.handlers.admin_payments import (
    build_review_payments_text,
)
from app.bot.keyboards.subscription import (
    get_payment_support_keyboard,
)
from app.database.models.course import Course
from app.database.models.payment import Payment
from app.database.models.subscription import (
    Subscription,
)
from app.database.models.subscription_event import (
    SubscriptionEvent,
)
from app.database.models.user import User
from app.services.payment_service import (
    PaymentError,
    cancel_payment,
    create_payment,
    get_review_payments_for_course,
    process_telegram_stars_payment,
    retry_payment_activation,
)

DATABASE_URL = os.environ["DATABASE_URL"]


def test_empty_payment_review_text():
    text = build_review_payments_text(
        course_title="Python Practice",
        payments=[],
    )

    assert text == (
        "💳 <b>Платежи на проверке</b>\n"
        "\n"
        "Курс: <b>Python Practice</b>\n"
        "\n"
        "✅ Платежей, требующих проверки, нет."
    )


def test_payment_support_command_returns_to_course_list():
    keyboard = get_payment_support_keyboard()

    back_button = keyboard.inline_keyboard[-1][0]

    assert back_button.text == "⬅️ К выбору уровня"
    assert back_button.callback_data == "nav:courses"


def test_course_payment_support_returns_to_subscription():
    keyboard = get_payment_support_keyboard("python_start")

    back_button = keyboard.inline_keyboard[-1][0]

    assert back_button.text == "⬅️ Назад к подписке"
    assert back_button.callback_data == ("menu:subscription:python_start")


async def create_test_payment(
    *,
    suffix: str,
    telegram_id: int,
) -> tuple[int, int, int]:
    engine = create_async_engine(DATABASE_URL)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            user = User(
                telegram_id=telegram_id,
                username=(f"payment_user_{suffix}"),
                first_name="Test",
            )

            session.add(user)
            await session.flush()

            course = Course(
                slug=(f"payment_course_{suffix}"),
                title="Payment test",
                requires_subscription=True,
                is_active=True,
            )

            session.add(course)
            await session.flush()

            payment = Payment(
                user_id=user.id,
                course_id=course.id,
                provider="telegram_stars",
                amount=150,
                currency="XTR",
                subscription_days=30,
                status="pending",
            )

            session.add(payment)
            await session.commit()

            return (
                payment.id,
                user.id,
                course.id,
            )

    finally:
        await engine.dispose()


async def get_payment(
    payment_id: int,
) -> Payment:
    engine = create_async_engine(DATABASE_URL)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            result = await session.execute(
                select(Payment).where(Payment.id == payment_id)
            )

            return result.scalar_one()

    finally:
        await engine.dispose()


async def get_subscription(
    *,
    user_id: int,
    course_id: int,
) -> Subscription | None:
    engine = create_async_engine(DATABASE_URL)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            result = await session.execute(
                select(Subscription).where(
                    Subscription.user_id == user_id,
                    Subscription.course_id == course_id,
                )
            )

            return result.scalar_one_or_none()

    finally:
        await engine.dispose()


async def get_subscription_events(
    *,
    user_id: int,
    course_id: int,
) -> list[SubscriptionEvent]:
    engine = create_async_engine(DATABASE_URL)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            result = await session.execute(
                select(SubscriptionEvent)
                .where(
                    SubscriptionEvent.user_id == user_id,
                    SubscriptionEvent.course_id == course_id,
                )
                .order_by(SubscriptionEvent.id)
            )

            return list(result.scalars().all())

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_successful_payment_is_idempotent():
    telegram_id = 900000101

    (
        payment_id,
        user_id,
        course_id,
    ) = await create_test_payment(
        suffix="idempotency",
        telegram_id=telegram_id,
    )

    first_result = await process_telegram_stars_payment(
        payment_id=payment_id,
        telegram_user_id=telegram_id,
        telegram_payment_charge_id=("charge_idempotency"),
        currency="XTR",
        total_amount=150,
    )

    assert first_result is not None
    assert first_result.subscription_days == 30

    first_payment = await get_payment(payment_id)

    first_subscription = await get_subscription(
        user_id=user_id,
        course_id=course_id,
    )

    assert first_payment.status == "succeeded"
    assert first_payment.external_payment_id == "charge_idempotency"
    assert first_payment.paid_at is not None

    assert first_subscription is not None

    first_ends_at = first_subscription.ends_at

    first_events = await get_subscription_events(
        user_id=user_id,
        course_id=course_id,
    )

    assert len(first_events) == 1

    first_event = first_events[0]

    assert first_event.subscription_id == first_subscription.id
    assert first_event.actor_telegram_id == telegram_id
    assert first_event.event_type == "activate_or_extend"
    assert first_event.source == "payment"
    assert first_event.reason == "telegram_stars_payment"
    assert first_event.days == 30
    assert first_event.old_status is None
    assert first_event.new_status == "active"
    assert first_event.idempotency_key == f"payment:{payment_id}"

    second_result = await process_telegram_stars_payment(
        payment_id=payment_id,
        telegram_user_id=telegram_id,
        telegram_payment_charge_id=("charge_idempotency"),
        currency="XTR",
        total_amount=150,
    )

    assert second_result is not None

    assert second_result.course_slug == "payment_course_idempotency"

    assert second_result.subscription_days == 30

    second_subscription = await get_subscription(
        user_id=user_id,
        course_id=course_id,
    )

    assert second_subscription is not None

    assert second_subscription.ends_at == first_ends_at

    second_events = await get_subscription_events(
        user_id=user_id,
        course_id=course_id,
    )

    assert len(second_events) == 1
    assert second_events[0].id == first_event.id


@pytest.mark.asyncio
async def test_cancelled_payment_can_still_succeed():
    telegram_id = 900000102

    (
        payment_id,
        user_id,
        course_id,
    ) = await create_test_payment(
        suffix="cancelled",
        telegram_id=telegram_id,
    )

    cancelled = await cancel_payment(
        payment_id=payment_id,
        telegram_user_id=telegram_id,
        course_slug="payment_course_cancelled",
    )

    assert cancelled is True

    payment = await get_payment(payment_id)

    assert payment.status == "cancelled"

    processed = await process_telegram_stars_payment(
        payment_id=payment_id,
        telegram_user_id=telegram_id,
        telegram_payment_charge_id=("charge_cancelled"),
        currency="XTR",
        total_amount=150,
    )

    assert processed is not None
    assert processed.subscription_days == 30

    payment = await get_payment(payment_id)

    assert payment.status == "succeeded"

    subscription = await get_subscription(
        user_id=user_id,
        course_id=course_id,
    )

    assert subscription is not None


@pytest.mark.parametrize(
    (
        "wrong_field",
        "telegram_id",
        "currency",
        "amount",
    ),
    [
        (
            "user",
            999999999,
            "XTR",
            150,
        ),
        (
            "currency",
            900000103,
            "RUB",
            150,
        ),
        (
            "amount",
            900000104,
            "XTR",
            999,
        ),
    ],
)
@pytest.mark.asyncio
async def test_invalid_payment_data_does_not_activate_subscription(
    wrong_field: str,
    telegram_id: int,
    currency: str,
    amount: int,
):
    actual_telegram_id = {
        "user": 900000105,
        "currency": 900000103,
        "amount": 900000104,
    }[wrong_field]

    (
        payment_id,
        user_id,
        course_id,
    ) = await create_test_payment(
        suffix=f"invalid_{wrong_field}",
        telegram_id=actual_telegram_id,
    )

    with pytest.raises(PaymentError):
        await process_telegram_stars_payment(
            payment_id=payment_id,
            telegram_user_id=telegram_id,
            telegram_payment_charge_id=(f"charge_invalid_{wrong_field}"),
            currency=currency,
            total_amount=amount,
        )

    payment = await get_payment(payment_id)

    assert payment.status == "pending"

    assert payment.external_payment_id is None

    subscription = await get_subscription(
        user_id=user_id,
        course_id=course_id,
    )

    assert subscription is None


async def mark_test_payment_review(
    *,
    payment_id: int,
    external_payment_id: str,
    error_message: str,
) -> None:
    engine = create_async_engine(DATABASE_URL)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            payment = await session.get(
                Payment,
                payment_id,
            )

            assert payment is not None

            payment.status = "review"
            payment.external_payment_id = external_payment_id
            payment.error_message = error_message

            await session.commit()

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_review_payment_can_be_retried():
    telegram_id = 900000106
    suffix = "review_retry"

    (
        payment_id,
        user_id,
        course_id,
    ) = await create_test_payment(
        suffix=suffix,
        telegram_id=telegram_id,
    )

    await mark_test_payment_review(
        payment_id=payment_id,
        external_payment_id=("charge_review_retry"),
        error_message=("Temporary activation error"),
    )

    course_slug = f"payment_course_{suffix}"

    review_payments = await get_review_payments_for_course(course_slug)

    assert len(review_payments) == 1

    review_payment = review_payments[0]

    assert review_payment.id == payment_id
    assert review_payment.telegram_user_id == telegram_id
    assert review_payment.error_message == "Temporary activation error"

    activated = await retry_payment_activation(payment_id=payment_id)

    assert activated is True

    payment = await get_payment(payment_id)

    assert payment.status == "succeeded"
    assert payment.error_message is None

    subscription = await get_subscription(
        user_id=user_id,
        course_id=course_id,
    )

    assert subscription is not None

    review_payments = await get_review_payments_for_course(course_slug)

    assert review_payments == []

    second_activation = await retry_payment_activation(payment_id=payment_id)

    assert second_activation is False


@pytest.mark.asyncio
async def test_cancel_payment_rejects_wrong_course():
    telegram_id = 900000107

    (
        payment_id,
        _,
        _,
    ) = await create_test_payment(
        suffix="cancel_wrong_course",
        telegram_id=telegram_id,
    )

    with pytest.raises(
        PaymentError,
        match="другому курсу",
    ):
        await cancel_payment(
            payment_id=payment_id,
            telegram_user_id=telegram_id,
            course_slug="wrong-course",
        )

    payment = await get_payment(payment_id)

    assert payment.status == "pending"


@pytest.mark.asyncio
async def test_repeated_purchase_reuses_pending_payment():
    suffix = uuid4().hex[:12]

    telegram_id = 8_300_000_000_000 + uuid4().int % 1_000_000_000_000

    course_slug = f"payment_reuse_{suffix}"

    engine = create_async_engine(DATABASE_URL)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            user = User(
                telegram_id=telegram_id,
                username=f"payment_reuse_{suffix}",
                first_name="Test",
            )

            course = Course(
                slug=course_slug,
                title="Payment reuse",
                requires_subscription=True,
                is_active=True,
            )

            session.add_all(
                [
                    user,
                    course,
                ]
            )

            await session.commit()

        async def create() -> int:
            payment = await create_payment(
                telegram_user_id=telegram_id,
                course_slug=course_slug,
                provider="telegram_stars",
                amount=150,
                subscription_days=30,
            )

            return payment.id

        first_id, second_id = await asyncio.gather(
            create(),
            create(),
        )

        assert first_id == second_id

        async with session_factory() as session:
            result = await session.execute(
                select(Payment).where(Payment.id == first_id)
            )

            payments = list(result.scalars().all())

            assert len(payments) == 1
            assert payments[0].status == "pending"
            assert payments[0].currency == "XTR"

    finally:
        await engine.dispose()
