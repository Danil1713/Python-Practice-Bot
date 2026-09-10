from dataclasses import dataclass
from datetime import datetime, timezone

from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.payment_repository import (
    PaymentRepository,
)
from app.database.repositories.user_repository import (
    UserRepository,
)
from app.database.session import (
    async_session_factory,
)
from app.services.subscription_service import activate_or_extend_subscription_in_session


class PaymentError(Exception):
    pass


class PaymentNotFound(PaymentError):
    pass


class PaymentAlreadyProcessed(PaymentError):
    pass


@dataclass(frozen=True)
class CreatedPayment:
    id: int
    user_id: int
    course_id: int
    amount: int
    currency: str
    subscription_days: int
    status: str

@dataclass(frozen=True)
class PaymentCheckoutView:
    id: int
    telegram_user_id: int
    course_id: int
    status: str
    amount: int
    currency: str
    subscription_days: int

async def create_payment(
    *,
    telegram_user_id: int,
    course_slug: str,
    provider: str,
    amount: int,
    subscription_days: int,
    currency: str = "RUB",
) -> CreatedPayment:
    if amount <= 0:
        raise PaymentError(
            "Стоимость должна быть больше 0."
        )

    if subscription_days <= 0:
        raise PaymentError(
            "Срок подписки должен быть больше 0."
        )

    async with async_session_factory() as session:
        user_repository = UserRepository(
            session
        )
        course_repository = CourseRepository(
            session
        )
        payment_repository = PaymentRepository(
            session
        )

        user = await user_repository.get_by_telegram_id(
            telegram_user_id
        )

        if user is None:
            raise PaymentError(
                "Пользователь не найден."
            )

        course = await course_repository.get_by_slug(
            course_slug
        )

        if course is None:
            raise PaymentError(
                "Курс не найден."
            )

        if not course.requires_subscription:
            raise PaymentError(
                "Для этого курса подписка не требуется."
            )

        payment = await payment_repository.create(
            user_id=user.id,
            course_id=course.id,
            provider=provider,
            amount=amount,
            currency=currency,
            subscription_days=subscription_days,
        )

        await session.commit()

        return CreatedPayment(
            id=payment.id,
            user_id=payment.user_id,
            course_id=payment.course_id,
            amount=payment.amount,
            currency=payment.currency,
            subscription_days=(
                payment.subscription_days
            ),
            status=payment.status,
        )

async def process_successful_payment(
    *,
    external_payment_id: str,
) -> bool:
    now = datetime.now(
        timezone.utc
    )

    async with async_session_factory() as session:
        payment_repository = PaymentRepository(
            session
        )

        payment = (
            await payment_repository
            .get_by_external_id(
                external_payment_id
            )
        )

        if payment is None:
            raise PaymentNotFound(
                "Платёж не найден."
            )

        if payment.status == "succeeded":
            return False

        await activate_or_extend_subscription_in_session(
            session=session,
            user_id=payment.user_id,
            course_id=payment.course_id,
            days=payment.subscription_days,
        )

        await payment_repository.mark_succeeded(
            payment=payment,
            paid_at=now,
        )

        await session.commit()

        return True

async def get_payment_checkout_view(
    payment_id: int,
) -> PaymentCheckoutView | None:
    async with async_session_factory() as session:
        payment_repository = PaymentRepository(
            session
        )
        user_repository = UserRepository(
            session
        )

        payment = await payment_repository.get_by_id(
            payment_id
        )

        if payment is None:
            return None

        user = await user_repository.get_by_id(
            payment.user_id
        )

        if user is None:
            return None

        return PaymentCheckoutView(
            id=payment.id,
            telegram_user_id=user.telegram_id,
            course_id=payment.course_id,
            status=payment.status,
            amount=payment.amount,
            currency=payment.currency,
            subscription_days=(
                payment.subscription_days
            ),
        )

async def process_telegram_stars_payment(
    *,
    payment_id: int,
    telegram_user_id: int,
    telegram_payment_charge_id: str,
    currency: str,
    total_amount: int,
) -> bool:
    now = datetime.now(
        timezone.utc
    )

    async with async_session_factory() as session:
        payment_repository = PaymentRepository(
            session
        )
        user_repository = UserRepository(
            session
        )

        payment = (
            await payment_repository
            .get_by_id_for_update(
                payment_id
            )
        )

        if payment is None:
            raise PaymentNotFound(
                "Платёж не найден."
            )

        if payment.status == "succeeded":
            return False

        if payment.status not in {
            "pending",
            "cancelled",
        }:
            raise PaymentError(
                "Платёж уже нельзя обработать."
            )

        user = await user_repository.get_by_id(
            payment.user_id
        )

        if user is None:
            raise PaymentError(
                "Пользователь не найден."
            )

        if user.telegram_id != telegram_user_id:
            raise PaymentError(
                "Платёж принадлежит "
                "другому пользователю."
            )

        if currency != payment.currency:
            raise PaymentError(
                "Валюта платежа не совпадает."
            )

        if total_amount != payment.amount:
            raise PaymentError(
                "Сумма платежа не совпадает."
            )

        await payment_repository.set_external_id(
            payment,
            telegram_payment_charge_id,
        )

        await activate_or_extend_subscription_in_session(
            session=session,
            user_id=payment.user_id,
            course_id=payment.course_id,
            days=payment.subscription_days,
        )

        await payment_repository.mark_succeeded(
            payment=payment,
            paid_at=now,
        )

        await session.commit()

        return True


async def cancel_payment(
    *,
    payment_id: int,
    telegram_user_id: int,
) -> bool:
    async with async_session_factory() as session:
        payment_repository = PaymentRepository(
            session
        )
        user_repository = UserRepository(
            session
        )

        payment = (
            await payment_repository
            .get_by_id_for_update(
                payment_id
            )
        )

        if payment is None:
            raise PaymentNotFound(
                "Платёж не найден."
            )

        user = await user_repository.get_by_id(
            payment.user_id
        )

        if (
            user is None
            or user.telegram_id != telegram_user_id
        ):
            raise PaymentError(
                "Этот платёж принадлежит "
                "другому пользователю."
            )

        if payment.status != "pending":
            return False

        await payment_repository.mark_cancelled(
            payment
        )

        await session.commit()

        return True
