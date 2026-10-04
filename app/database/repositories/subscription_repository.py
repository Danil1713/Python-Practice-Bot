from datetime import datetime, timezone

from sqlalchemy import (
    and_,
    func,
    or_,
    select,
)
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

    async def get_revocation_candidate_ids(
        self,
        *,
        now: datetime,
        stale_before: datetime,
        limit: int = 50,
    ) -> list[int]:
        statement = (
            select(Subscription.id)
            .where(
                or_(
                    and_(
                        Subscription.status == "active",
                        Subscription.ends_at <= now,
                    ),
                    and_(
                        Subscription.status == "revoking",
                        Subscription.updated_at <= stale_before,
                    ),
                )
            )
            .order_by(Subscription.ends_at.asc())
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def get_by_id_for_update(
        self,
        subscription_id: int,
    ) -> Subscription | None:
        statement = (
            select(Subscription)
            .where(Subscription.id == subscription_id)
            .with_for_update()
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def mark_revoking(
        self,
        subscription: Subscription,
        started_at: datetime,
    ) -> None:
        subscription.status = "revoking"
        subscription.updated_at = started_at

        await self.session.flush()

    async def restore_active(
        self,
        subscription: Subscription,
    ) -> None:
        subscription.status = "active"

        await self.session.flush()

    async def mark_cancelled(
        self,
        subscription: Subscription,
    ) -> None:
        subscription.status = "cancelled"

        await self.session.flush()
