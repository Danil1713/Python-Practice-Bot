from datetime import datetime, timezone

from sqlalchemy import select
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

        statement = select(
            Subscription
        ).where(
            Subscription.user_id == user_id,
            Subscription.course_id == course_id,
            Subscription.status == "active",
            Subscription.starts_at <= now,
            Subscription.ends_at > now,
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()