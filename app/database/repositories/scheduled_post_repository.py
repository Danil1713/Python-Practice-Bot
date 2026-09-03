from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.scheduled_post import (
    ScheduledPost,
)


class ScheduledPostRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_due(
        self,
        now: datetime,
        limit: int = 10,
    ) -> list[ScheduledPost]:
        statement = (
            select(ScheduledPost)
            .where(
                ScheduledPost.status
                == "scheduled",
                ScheduledPost.scheduled_at
                <= now,
            )
            .order_by(
                ScheduledPost.scheduled_at
            )
            .limit(limit)
        )

        result = await self.session.execute(
            statement
        )

        return list(
            result.scalars().all()
        )

    async def get_by_id(
        self,
        post_id: int,
    ) -> ScheduledPost | None:
        statement = select(
            ScheduledPost
        ).where(
            ScheduledPost.id == post_id
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def mark_publishing(
            self,
            post: ScheduledPost,
    ) -> None:
        post.status = "publishing"
        post.publishing_started_at = datetime.now(
            timezone.utc
        )
        post.error_message = None

        await self.session.flush()

    async def mark_published(
            self,
            post: ScheduledPost,
            published_at: datetime,
            telegram_message_id: int,
    ) -> None:
        post.status = "published"
        post.publishing_started_at = None
        post.published_at = published_at
        post.telegram_message_id = (
            telegram_message_id
        )
        post.error_message = None

        await self.session.flush()

    async def mark_failed(
            self,
            post: ScheduledPost,
            error_message: str,
    ) -> None:
        post.status = "failed"
        post.publishing_started_at = None
        post.error_message = error_message

        await self.session.flush()

    async def recover_stuck(
            self,
            before: datetime,
    ) -> int:
        statement = select(
            ScheduledPost
        ).where(
            ScheduledPost.status == "publishing",
            ScheduledPost.publishing_started_at.is_not(
                None
            ),
            ScheduledPost.publishing_started_at
            <= before,
        )

        result = await self.session.execute(
            statement
        )

        posts = list(
            result.scalars().all()
        )

        for post in posts:
            post.status = "scheduled"
            post.publishing_started_at = None

        await self.session.flush()

        return len(posts)