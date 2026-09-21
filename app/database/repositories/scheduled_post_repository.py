from datetime import datetime, timezone

from sqlalchemy import select, update
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
            post.status = "failed"
            post.publishing_started_at = None
            post.error_message = (
                "Не удалось однозначно определить "
                "результат публикации после сбоя. "
                "Проверь Telegram-канал перед "
                "повторной публикацией."
            )

        await self.session.flush()

        return len(posts)

    async def create(
            self,
            *,
            course_id: int,
            post_type: str,
            content: str,
            scheduled_at: datetime,
            project_id: int | None = None,
            hint_id: int | None = None,
    ) -> ScheduledPost:
        post = ScheduledPost(
            course_id=course_id,
            post_type=post_type,
            project_id=project_id,
            hint_id=hint_id,
            content=content,
            scheduled_at=scheduled_at,
            status="scheduled",
        )

        self.session.add(post)

        await self.session.flush()

        return post

    async def reschedule(
            self,
            post: ScheduledPost,
            scheduled_at: datetime,
    ) -> None:
        post.scheduled_at = scheduled_at
        post.status = "scheduled"
        post.error_message = None

        await self.session.flush()

    async def cancel(
            self,
            post: ScheduledPost,
    ) -> None:
        post.status = "cancelled"

        await self.session.flush()

    async def get_manageable_by_course(
            self,
            course_id: int,
    ) -> list[ScheduledPost]:
        statement = (
            select(ScheduledPost)
            .where(
                ScheduledPost.course_id == course_id,
                ScheduledPost.status.in_(
                    [
                        "scheduled",
                        "failed",
                    ]
                ),
            )
            .order_by(
                ScheduledPost.scheduled_at
            )
        )

        result = await self.session.execute(
            statement
        )

        return list(
            result.scalars().all()
        )

    async def claim_scheduled(
            self,
            post_id: int,
    ) -> bool:
        started_at = datetime.now(
            timezone.utc
        )

        statement = (
            update(ScheduledPost)
            .where(
                ScheduledPost.id == post_id,
                ScheduledPost.status == "scheduled",
            )
            .values(
                status="publishing",
                publishing_started_at=started_at,
                error_message=None,
            )
            .returning(
                ScheduledPost.id
            )
        )

        result = await self.session.execute(
            statement
        )

        claimed_id = result.scalar_one_or_none()

        return claimed_id is not None

    async def has_active_for_project(
            self,
            project_id: int,
            exclude_post_id: int | None = None,
    ) -> bool:
        conditions = [
            ScheduledPost.project_id == project_id,
            ScheduledPost.status.in_(
                [
                    "scheduled",
                    "publishing",
                ]
            ),
        ]

        if exclude_post_id is not None:
            conditions.append(
                ScheduledPost.id != exclude_post_id
            )

        statement = (
            select(ScheduledPost.id)
            .where(*conditions)
            .limit(1)
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none() is not None

    async def has_active_for_hint(
            self,
            hint_id: int,
            exclude_post_id: int | None = None,
    ) -> bool:
        conditions = [
            ScheduledPost.hint_id == hint_id,
            ScheduledPost.status.in_(
                [
                    "scheduled",
                    "publishing",
                ]
            ),
        ]

        if exclude_post_id is not None:
            conditions.append(
                ScheduledPost.id != exclude_post_id
            )

        statement = (
            select(ScheduledPost.id)
            .where(*conditions)
            .limit(1)
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none() is not None