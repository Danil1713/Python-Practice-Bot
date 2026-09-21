from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.payment import Payment


class PaymentRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        course_id: int,
        provider: str,
        amount: int,
        currency: str,
        subscription_days: int,
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            course_id=course_id,
            provider=provider,
            amount=amount,
            currency=currency,
            subscription_days=subscription_days,
            status="pending",
        )

        self.session.add(payment)

        await self.session.flush()

        return payment

    async def get_by_id(
        self,
        payment_id: int,
    ) -> Payment | None:
        statement = select(
            Payment
        ).where(
            Payment.id == payment_id
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def get_by_external_id(
        self,
        external_payment_id: str,
    ) -> Payment | None:
        statement = select(
            Payment
        ).where(
            Payment.external_payment_id
            == external_payment_id
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def set_external_id(
        self,
        payment: Payment,
        external_payment_id: str,
    ) -> None:
        payment.external_payment_id = (
            external_payment_id
        )

        await self.session.flush()

    async def mark_succeeded(
            self,
            payment: Payment,
            paid_at: datetime,
    ) -> None:
        payment.status = "succeeded"
        payment.paid_at = paid_at
        payment.error_message = None

        await self.session.flush()

    async def mark_cancelled(
        self,
        payment: Payment,
    ) -> None:
        payment.status = "cancelled"

        await self.session.flush()

    async def get_by_id_for_update(
            self,
            payment_id: int,
    ) -> Payment | None:
        statement = (
            select(Payment)
            .where(
                Payment.id == payment_id
            )
            .with_for_update()
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def mark_pre_checkout(
            self,
            payment: Payment,
            at: datetime,
    ) -> None:
        payment.pre_checkout_at = at
        payment.error_message = None

        await self.session.flush()

    async def mark_review(
            self,
            payment: Payment,
            error_message: str,
    ) -> None:
        payment.status = "review"
        payment.error_message = error_message

        await self.session.flush()

    async def get_stale_pre_checkout(
            self,
            before: datetime,
            limit: int = 100,
    ) -> list[Payment]:
        statement = (
            select(Payment)
            .where(
                Payment.status == "pending",
                Payment.pre_checkout_at.is_not(None),
                Payment.pre_checkout_at <= before,
            )
            .order_by(
                Payment.pre_checkout_at
            )
            .limit(limit)
            .with_for_update(
                skip_locked=True
            )
        )

        result = await self.session.execute(
            statement
        )

        return list(
            result.scalars().all()
        )