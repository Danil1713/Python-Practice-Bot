import logging
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

logger = logging.getLogger(__name__)

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

@dataclass(frozen=True)
class ProcessedPayment:
    course_slug: str
    subscription_days: int

@dataclass(frozen=True)
class ReviewPaymentItem:
    id: int
    telegram_user_id: int
    username: str | None
    course_slug: str
    course_title: str
    amount: int
    currency: str
    subscription_days: int
    external_payment_id: str | None
    error_message: str | None
    created_at: datetime

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

async def _process_telegram_stars_payment(
    *,
    payment_id: int,
    telegram_user_id: int,
    telegram_payment_charge_id: str,
    currency: str,
    total_amount: int,
) -> ProcessedPayment:
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

        course_repository = CourseRepository(
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

        if payment.status not in {
            "pending",
            "cancelled",
            "review",
            "succeeded",
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

        course = await course_repository.get_by_id(
            payment.course_id
        )

        if course is None:
            raise PaymentError(
                "Курс не найден."
            )

        if (
            user.telegram_id
            != telegram_user_id
        ):
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

        existing = (
            await payment_repository
            .get_by_external_id(
                telegram_payment_charge_id
            )
        )

        if (
            existing is not None
            and existing.id != payment.id
        ):
            raise PaymentError(
                "Telegram charge уже связан "
                "с другим платежом."
            )

        if (
            payment.external_payment_id
            is not None
            and payment.external_payment_id
            != telegram_payment_charge_id
        ):
            raise PaymentError(
                "Идентификатор платежа "
                "не совпадает."
            )

        if payment.status == "succeeded":
            return ProcessedPayment(
                course_slug=course.slug,
                subscription_days=(
                    payment.subscription_days
                ),
            )

        if payment.external_payment_id is None:
            await payment_repository.set_external_id(
                payment,
                telegram_payment_charge_id,
            )

        await (
            activate_or_extend_subscription_in_session(
                session=session,
                user_id=payment.user_id,
                course_id=payment.course_id,
                days=payment.subscription_days,
            )
        )

        await payment_repository.mark_succeeded(
            payment=payment,
            paid_at=now,
        )

        await session.commit()

        return ProcessedPayment(
            course_slug=course.slug,
            subscription_days=payment.subscription_days,
        )

async def process_telegram_stars_payment(
    *,
    payment_id: int,
    telegram_user_id: int,
    telegram_payment_charge_id: str,
    currency: str,
    total_amount: int,
) -> ProcessedPayment:
    try:
        return await (
            _process_telegram_stars_payment(
                payment_id=payment_id,
                telegram_user_id=(
                    telegram_user_id
                ),
                telegram_payment_charge_id=(
                    telegram_payment_charge_id
                ),
                currency=currency,
                total_amount=total_amount,
            )
        )

    except PaymentError:
        logger.warning(
            "Telegram Stars payment rejected "
            "payment_id=%s "
            "telegram_user_id=%s "
            "charge_id=%s",
            payment_id,
            telegram_user_id,
            telegram_payment_charge_id,
        )

        raise

    except Exception as error:
        logger.exception(
            "Telegram Stars processing failed "
            "payment_id=%s "
            "telegram_user_id=%s "
            "charge_id=%s",
            payment_id,
            telegram_user_id,
            telegram_payment_charge_id,
        )

        try:
            await mark_payment_for_review(
                payment_id=payment_id,
                telegram_payment_charge_id=(
                    telegram_payment_charge_id
                ),
                error_message=str(error),
            )

        except Exception:
            logger.exception(
                "Failed to mark payment "
                "for review "
                "payment_id=%s",
                payment_id,
            )

        raise PaymentError(
            "Не удалось активировать подписку."
        ) from error


async def cancel_payment(
    *,
    payment_id: int,
    telegram_user_id: int,
    course_slug: str,
) -> bool:
    async with async_session_factory() as session:
        payment_repository = PaymentRepository(
            session
        )
        user_repository = UserRepository(
            session
        )
        course_repository = CourseRepository(
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
            or user.telegram_id
            != telegram_user_id
        ):
            raise PaymentError(
                "Этот платёж принадлежит "
                "другому пользователю."
            )

        course = await course_repository.get_by_id(
            payment.course_id
        )

        if course is None:
            raise PaymentError(
                "Курс платежа не найден."
            )

        if course.slug != course_slug:
            raise PaymentError(
                "Платёж относится "
                "к другому курсу."
            )

        if payment.status != "pending":
            return False

        await payment_repository.mark_cancelled(
            payment
        )

        await session.commit()

        return True

async def approve_pre_checkout(
    *,
    payment_id: int,
    telegram_user_id: int,
    currency: str,
    total_amount: int,
) -> None:
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

        if payment.status != "pending":
            raise PaymentError(
                "Этот платёж уже обработан."
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

        if payment.currency != currency:
            raise PaymentError(
                "Некорректная валюта."
            )

        if payment.amount != total_amount:
            raise PaymentError(
                "Некорректная сумма."
            )

        await payment_repository.mark_pre_checkout(
            payment=payment,
            at=now,
        )

        await session.commit()


async def get_review_payments_for_course(
    course_slug: str,
) -> list[ReviewPaymentItem]:
    async with async_session_factory() as session:
        payment_repository = PaymentRepository(
            session
        )
        user_repository = UserRepository(
            session
        )
        course_repository = CourseRepository(
            session
        )

        course = await course_repository.get_by_slug(
            course_slug
        )

        if course is None:
            raise PaymentError(
                "Курс не найден."
            )

        payments = (
            await payment_repository
            .get_review_payments(
                course_id=course.id,
            )
        )

        result: list[ReviewPaymentItem] = []

        for payment in payments:
            user = await user_repository.get_by_id(
                payment.user_id
            )

            if user is None:
                continue

            result.append(
                ReviewPaymentItem(
                    id=payment.id,
                    telegram_user_id=(
                        user.telegram_id
                    ),
                    username=user.username,
                    course_slug=course.slug,
                    course_title=course.title,
                    amount=payment.amount,
                    currency=payment.currency,
                    subscription_days=(
                        payment.subscription_days
                    ),
                    external_payment_id=(
                        payment.external_payment_id
                    ),
                    error_message=(
                        payment.error_message
                    ),
                    created_at=payment.created_at,
                )
            )

        return result


async def get_review_payment_detail(
    *,
    payment_id: int,
    course_slug: str,
) -> ReviewPaymentItem | None:
    async with async_session_factory() as session:
        payment_repository = PaymentRepository(
            session
        )
        user_repository = UserRepository(
            session
        )
        course_repository = CourseRepository(
            session
        )

        course = await course_repository.get_by_slug(
            course_slug
        )

        if course is None:
            return None

        payment = await payment_repository.get_by_id(
            payment_id
        )

        if (
            payment is None
            or payment.status != "review"
            or payment.course_id != course.id
        ):
            return None

        user = await user_repository.get_by_id(
            payment.user_id
        )

        if user is None:
            return None

        return ReviewPaymentItem(
            id=payment.id,
            telegram_user_id=user.telegram_id,
            username=user.username,
            course_slug=course.slug,
            course_title=course.title,
            amount=payment.amount,
            currency=payment.currency,
            subscription_days=(
                payment.subscription_days
            ),
            external_payment_id=(
                payment.external_payment_id
            ),
            error_message=payment.error_message,
            created_at=payment.created_at,
        )


async def mark_payment_for_review(
    *,
    payment_id: int,
    telegram_payment_charge_id: str,
    error_message: str,
) -> None:
    async with async_session_factory() as session:
        repository = PaymentRepository(
            session
        )

        payment = await repository.get_by_id_for_update(
            payment_id
        )

        if payment is None:
            return

        if payment.status == "succeeded":
            return

        if payment.external_payment_id is None:
            existing = await repository.get_by_external_id(
                telegram_payment_charge_id
            )

            if (
                existing is None
                or existing.id == payment.id
            ):
                await repository.set_external_id(
                    payment,
                    telegram_payment_charge_id,
                )

        await repository.mark_review(
            payment,
            error_message,
        )

        await session.commit()

async def retry_payment_activation(
    *,
    payment_id: int,
) -> bool:
    now = datetime.now(
        timezone.utc
    )

    async with async_session_factory() as session:
        repository = PaymentRepository(
            session
        )

        payment = await repository.get_by_id_for_update(
            payment_id
        )

        if payment is None:
            raise PaymentNotFound(
                "Платёж не найден."
            )

        if payment.status == "succeeded":
            return False

        if payment.status != "review":
            raise PaymentError(
                "Платёж не требует сверки."
            )

        if payment.external_payment_id is None:
            raise PaymentError(
                "Нет подтверждённого "
                "Telegram charge ID."
            )

        await activate_or_extend_subscription_in_session(
            session=session,
            user_id=payment.user_id,
            course_id=payment.course_id,
            days=payment.subscription_days,
        )

        await repository.mark_succeeded(
            payment=payment,
            paid_at=now,
        )

        await session.commit()

        return True
