import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot

from app.database.repositories.scheduled_post_repository import (
    ScheduledPostRepository,
)
from app.database.session import (
    async_session_factory,
)
from app.services.publishing_service import (
    publish_scheduled_post,
)

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 30
STUCK_AFTER_MINUTES = 5


async def run_publishing_scheduler(
    bot: Bot,
) -> None:
    while True:
        try:
            now = datetime.now(
                timezone.utc
            )

            stuck_before = (
                    now
                    - timedelta(
                minutes=STUCK_AFTER_MINUTES
            )
            )

            async with async_session_factory() as session:
                repository = (
                    ScheduledPostRepository(
                        session
                    )
                )

                recovered = await repository.recover_stuck(
                    before=stuck_before
                )

                if recovered > 0:
                    logger.warning(
                        "Marked %s stuck posts "
                        "for manual review",
                        recovered,
                    )

                await session.commit()

                posts = await repository.get_due(
                    now
                )

                post_ids = [
                    post.id
                    for post in posts
                ]

            for post_id in post_ids:
                await publish_scheduled_post(
                    post_id=post_id,
                    bot=bot,
                )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Publishing scheduler failed"
            )

        await asyncio.sleep(
            CHECK_INTERVAL_SECONDS
        )