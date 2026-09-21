import os
from uuid import uuid4

import pytest
from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.models.course import Course
from app.database.models.subscription import (
    Subscription,
)
from app.database.models.subscription_event import (
    SubscriptionEvent,
)
from app.database.models.user import User
from app.services.admin_subscription_service import (
    activate_or_extend_subscription,
)


@pytest.mark.asyncio
async def test_admin_subscription_grant_is_idempotent():
    database_url = os.environ[
        "DATABASE_URL"
    ]

    engine = create_async_engine(
        database_url
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            user = User(
                telegram_id=900000201,
                username="admin_audit_user",
                first_name="Test",
            )

            session.add(user)
            await session.flush()

            course = Course(
                slug="admin_audit_course",
                title="Admin audit course",
                requires_subscription=True,
                is_active=True,
            )

            session.add(course)
            await session.commit()

            user_id = user.id
            course_id = course.id

        operation_id = uuid4().hex

        first_result = (
            await activate_or_extend_subscription(
                user_id=user_id,
                course_id=course_id,
                days=30,
                actor_telegram_id=700000001,
                idempotency_key=operation_id,
            )
        )

        second_result = (
            await activate_or_extend_subscription(
                user_id=user_id,
                course_id=course_id,
                days=30,
                actor_telegram_id=700000001,
                idempotency_key=operation_id,
            )
        )

        assert (
            second_result.ends_at
            == first_result.ends_at
        )

        async with session_factory() as session:
            event_count = await session.scalar(
                select(
                    func.count(
                        SubscriptionEvent.id
                    )
                ).where(
                    SubscriptionEvent.idempotency_key
                    == operation_id
                )
            )

            subscription = (
                await session.scalar(
                    select(
                        Subscription
                    ).where(
                        Subscription.user_id
                        == user_id,
                        Subscription.course_id
                        == course_id,
                    )
                )
            )

            event = await session.scalar(
                select(
                    SubscriptionEvent
                ).where(
                    SubscriptionEvent.idempotency_key
                    == operation_id
                )
            )

            assert subscription is not None
            assert event is not None

            assert event_count == 1

            assert (
                subscription.ends_at
                == first_result.ends_at
            )

            assert (
                event.actor_telegram_id
                == 700000001
            )

            assert event.source == "admin"

            assert (
                event.reason
                == "manual_admin_grant"
            )

            assert event.days == 30

    finally:
        await engine.dispose()