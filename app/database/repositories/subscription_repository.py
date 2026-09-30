from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.subscription import (
    Subscription,
)


class SubscriptionRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_active_subscription(
        self,
        user_id: int,
        course_id: int,
    ) -> Subscription | None:
        now = datetime.now(timezone.utc)

        statement = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.course_id == course_id,
            Subscription.status == "active",
            Subscription.starts_at <= now,
            Subscription.ends_at > now,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_user_and_course(
        self,
        user_id: int,
        course_id: int,
    ) -> Subscription | None:
        statement = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.course_id == course_id,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def save(
        self,
        subscription: Subscription,
    ) -> None:
        self.session.add(subscription)

        await self.session.flush()

    async def get_all_for_user(
        self,
        user_id: int,
    ) -> list[Subscription]:
        statement = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def lock_subscription(
        self,
        user_id: int,
        course_id: int,
    ) -> None:
        statement = select(
            func.pg_advisory_xact_lock(
                user_id,
                course_id,
            )
        )

        await self.session.execute(statement)
