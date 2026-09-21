import asyncio
import logging
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from app.database.repositories.payment_repository import (
    PaymentRepository,
)
from app.database.session import (
    async_session_factory,
)

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60
STUCK_AFTER_MINUTES = 15


async def mark_stale_payments_for_review() -> int:
    before = (
        datetime.now(timezone.utc)
        - timedelta(
            minutes=STUCK_AFTER_MINUTES
        )
    )

    async with async_session_factory() as session:
        repository = PaymentRepository(
            session
        )

        payments = (
            await repository.get_stale_pre_checkout(
                before=before
            )
        )

        for payment in payments:
            await repository.mark_review(
                payment,
                (
                    "Pre-checkout был подтверждён, "
                    "но successful_payment "
                    "не был получен вовремя."
                ),
            )

        await session.commit()

        return len(payments)


async def run_payment_recovery() -> None:
    while True:
        try:
            review_count = (
                await mark_stale_payments_for_review()
            )

            if review_count > 0:
                logger.warning(
                    "Marked %s payments "
                    "for reconciliation",
                    review_count,
                )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Payment recovery failed"
            )

        await asyncio.sleep(
            CHECK_INTERVAL_SECONDS
        )