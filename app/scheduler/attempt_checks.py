import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot

from app.database.repositories.attempt_repository import (
    AttemptRepository,
)
from app.database.session import (
    async_session_factory,
)
from app.services.attempt_check_service import (
    check_attempt,
)

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 5
BATCH_SIZE = 5
STUCK_AFTER_MINUTES = 5


async def get_pending_attempt_ids() -> list[int]:
    async with async_session_factory() as session:
        repository = AttemptRepository(
            session
        )

        before = (
            datetime.now(timezone.utc)
            - timedelta(
                minutes=STUCK_AFTER_MINUTES
            )
        )

        recovered = (
            await repository.recover_stuck_checking(
                before=before
            )
        )

        if recovered > 0:
            logger.warning(
                "Recovered %s stuck "
                "AI attempts",
                recovered,
            )

        await session.commit()

        attempts = await repository.get_pending(
            limit=BATCH_SIZE
        )

        return [
            attempt.id
            for attempt in attempts
        ]


async def run_attempt_check_worker(
    bot: Bot,
) -> None:
    while True:
        try:
            attempt_ids = (
                await get_pending_attempt_ids()
            )

            for attempt_id in attempt_ids:
                try:
                    await check_attempt(
                        attempt_id=attempt_id,
                        bot=bot,
                    )

                except asyncio.CancelledError:
                    raise

                except Exception:
                    logger.exception(
                        "Attempt check failed "
                        "attempt_id=%s",
                        attempt_id,
                    )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Attempt check worker "
                "iteration failed"
            )

        await asyncio.sleep(
            CHECK_INTERVAL_SECONDS
        )