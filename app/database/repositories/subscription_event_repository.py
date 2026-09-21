from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.database.models.subscription_event import (
    SubscriptionEvent,
)


class SubscriptionEventRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> SubscriptionEvent | None:
        statement = select(
            SubscriptionEvent
        ).where(
            SubscriptionEvent.idempotency_key
            == idempotency_key
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        subscription_id: int,
        user_id: int,
        course_id: int,
        actor_telegram_id: int,
        event_type: str,
        source: str,
        reason: str,
        days: int | None,
        old_status: str | None,
        new_status: str,
        old_starts_at: datetime | None,
        new_starts_at: datetime,
        old_ends_at: datetime | None,
        new_ends_at: datetime,
        idempotency_key: str,
    ) -> SubscriptionEvent:
        event = SubscriptionEvent(
            subscription_id=subscription_id,
            user_id=user_id,
            course_id=course_id,
            actor_telegram_id=(
                actor_telegram_id
            ),
            event_type=event_type,
            source=source,
            reason=reason,
            days=days,
            old_status=old_status,
            new_status=new_status,
            old_starts_at=old_starts_at,
            new_starts_at=new_starts_at,
            old_ends_at=old_ends_at,
            new_ends_at=new_ends_at,
            idempotency_key=idempotency_key,
        )

        self.session.add(event)

        await self.session.flush()

        return event