import os

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.models.course import Course
from app.database.models.payment import Payment
from app.database.models.subscription import (
    Subscription,
)
from app.database.models.user import User
from app.services.payment_service import (
    PaymentError,
    cancel_payment,
    process_telegram_stars_payment,
)


DATABASE_URL = os.environ[
    "DATABASE_URL"
]


async def create_test_payment(
    *,
    suffix: str,
    telegram_id: int,
) -> tuple[int, int, int]:
    engine = create_async_engine(
        DATABASE_URL
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            user = User(
                telegram_id=telegram_id,
                username=(
                    f"payment_user_{suffix}"
                ),
                first_name="Test",
            )

            session.add(user)
            await session.flush()

            course = Course(
                slug=(
                    f"payment_course_{suffix}"
                ),
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
    engine = create_async_engine(
        DATABASE_URL
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            result = await session.execute(
                select(Payment).where(
                    Payment.id
                    == payment_id
                )
            )

            return result.scalar_one()

    finally:
        await engine.dispose()


async def get_subscription(
    *,
    user_id: int,
    course_id: int,
) -> Subscription | None:
    engine = create_async_engine(
        DATABASE_URL
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            result = await session.execute(
                select(Subscription).where(
                    Subscription.user_id
                    == user_id,
                    Subscription.course_id
                    == course_id,
                )
            )

            return result.scalar_one_or_none()

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

    first_result = (
        await process_telegram_stars_payment(
            payment_id=payment_id,
            telegram_user_id=telegram_id,
            telegram_payment_charge_id=(
                "charge_idempotency"
            ),
            currency="XTR",
            total_amount=150,
        )
    )

    assert first_result is True

    first_payment = await get_payment(
        payment_id
    )

    first_subscription = (
        await get_subscription(
            user_id=user_id,
            course_id=course_id,
        )
    )

    assert first_payment.status == "succeeded"
    assert (
        first_payment.external_payment_id
        == "charge_idempotency"
    )
    assert first_payment.paid_at is not None

    assert first_subscription is not None

    first_ends_at = (
        first_subscription.ends_at
    )

    second_result = (
        await process_telegram_stars_payment(
            payment_id=payment_id,
            telegram_user_id=telegram_id,
            telegram_payment_charge_id=(
                "charge_idempotency"
            ),
            currency="XTR",
            total_amount=150,
        )
    )

    assert second_result is False

    second_subscription = (
        await get_subscription(
            user_id=user_id,
            course_id=course_id,
        )
    )

    assert second_subscription is not None

    assert (
        second_subscription.ends_at
        == first_ends_at
    )


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
    )

    assert cancelled is True

    payment = await get_payment(
        payment_id
    )

    assert payment.status == "cancelled"

    processed = (
        await process_telegram_stars_payment(
            payment_id=payment_id,
            telegram_user_id=telegram_id,
            telegram_payment_charge_id=(
                "charge_cancelled"
            ),
            currency="XTR",
            total_amount=150,
        )
    )

    assert processed is True

    payment = await get_payment(
        payment_id
    )

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

    with pytest.raises(
        PaymentError
    ):
        await process_telegram_stars_payment(
            payment_id=payment_id,
            telegram_user_id=telegram_id,
            telegram_payment_charge_id=(
                f"charge_invalid_{wrong_field}"
            ),
            currency=currency,
            total_amount=amount,
        )

    payment = await get_payment(
        payment_id
    )

    assert payment.status == "pending"

    assert (
        payment.external_payment_id
        is None
    )

    subscription = await get_subscription(
        user_id=user_id,
        course_id=course_id,
    )

    assert subscription is None