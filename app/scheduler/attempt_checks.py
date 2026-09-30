import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot

from app.config import get_ai_max_concurrency
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
SETUP_STUCK_AFTER_MINUTES = 2


async def get_pending_attempt_ids() -> list[int]:
    async with async_session_factory() as session:
        repository = AttemptRepository(session)

        setup_before = datetime.now(timezone.utc) - timedelta(
            minutes=SETUP_STUCK_AFTER_MINUTES
        )

        recovered_setup = await repository.recover_stuck_pending_setup(
            before=setup_before
        )

        if recovered_setup > 0:
            logger.warning(
                "Recovered %s stuck pending AI attempts without status message",
                recovered_setup,
            )

        before = datetime.now(timezone.utc) - timedelta(minutes=STUCK_AFTER_MINUTES)

        recovered = await repository.recover_stuck_checking(before=before)

        if recovered > 0:
            logger.warning(
                "Recovered %s stuck AI attempts",
                recovered,
            )

        await session.commit()

        attempts = await repository.get_pending(limit=BATCH_SIZE)

        return [attempt.id for attempt in attempts]


async def process_attempt(
    *,
    attempt_id: int,
    bot: Bot,
    semaphore: asyncio.Semaphore,
) -> None:
    async with semaphore:
        try:
            await check_attempt(
                attempt_id=attempt_id,
                bot=bot,
            )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Attempt check failed attempt_id=%s",
                attempt_id,
            )


async def process_attempt_batch(
    *,
    attempt_ids: list[int],
    bot: Bot,
    max_concurrency: int | None = None,
) -> None:
    if not attempt_ids:
        return

    concurrency = (
        max_concurrency if max_concurrency is not None else get_ai_max_concurrency()
    )

    if concurrency <= 0:
        raise ValueError("AI max concurrency must be greater than 0")

    semaphore = asyncio.Semaphore(concurrency)

    await asyncio.gather(
        *[
            process_attempt(
                attempt_id=attempt_id,
                bot=bot,
                semaphore=semaphore,
            )
            for attempt_id in attempt_ids
        ]
    )


async def run_attempt_check_worker(
    bot: Bot,
) -> None:
    while True:
        try:
            attempt_ids = await get_pending_attempt_ids()

            await process_attempt_batch(
                attempt_ids=attempt_ids,
                bot=bot,
            )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception("Attempt check worker iteration failed")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
