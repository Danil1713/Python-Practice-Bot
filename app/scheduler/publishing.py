import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot

from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.scheduled_post_repository import (
    ScheduledPostRepository,
)
from app.database.session import (
    async_session_factory,
)
from app.services.publishing_service import (
    notify_admins_about_publication_failure,
    publish_scheduled_post,
)

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 30
STUCK_AFTER_MINUTES = 5


async def recover_stuck_publications(
    *,
    bot: Bot,
    before: datetime,
) -> int:
    notifications = []

    async with async_session_factory() as session:
        post_repository = ScheduledPostRepository(session)
        course_repository = CourseRepository(session)

        posts = await post_repository.recover_stuck(before=before)

        for post in posts:
            course = await course_repository.get_by_id(post.course_id)

            notifications.append(
                (
                    post.id,
                    post.post_type,
                    course.slug if course is not None else None,
                    post.error_message
                    or "Неизвестная ошибка восстановления публикации.",
                )
            )

        await session.commit()

    for (
        post_id,
        post_type,
        course_slug,
        error_message,
    ) in notifications:
        await notify_admins_about_publication_failure(
            bot=bot,
            post_id=post_id,
            post_type=post_type,
            course_slug=course_slug,
            error_message=error_message,
        )

    return len(posts)


async def run_publishing_scheduler(
    bot: Bot,
) -> None:
    while True:
        try:
            now = datetime.now(timezone.utc)

            stuck_before = now - timedelta(minutes=STUCK_AFTER_MINUTES)

            recovered_count = await recover_stuck_publications(
                bot=bot,
                before=stuck_before,
            )

            if recovered_count > 0:
                logger.warning(
                    "Marked %s stuck posts for manual review",
                    recovered_count,
                )

            async with async_session_factory() as session:
                repository = ScheduledPostRepository(session)

                posts = await repository.get_due(now)

                post_ids = [post.id for post in posts]

            for post_id in post_ids:
                await publish_scheduled_post(
                    post_id=post_id,
                    bot=bot,
                )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception("Publishing scheduler failed")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
