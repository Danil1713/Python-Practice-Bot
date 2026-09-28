import asyncio
import os
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.models.course import Course
from app.database.models.subscription import (
    Subscription,
)
from app.database.models.user import User
from app.services.subscription_service import (
    activate_or_extend_subscription_in_session,
)


@pytest.mark.asyncio
async def test_concurrent_subscription_extensions_are_not_lost():
    suffix = uuid4().hex[:12]

    telegram_id = (
            8_000_000_000_000
            + uuid4().int % 1_000_000_000_000
    )

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
        now = datetime.now(
            timezone.utc
        )

        initial_ends_at = (
            now
            + timedelta(days=10)
        )

        async with session_factory() as session:
            user = User(
                telegram_id=telegram_id,
                username=(
                    f"subscription_test_{suffix}"
                ),
                first_name="Test",
            )

            session.add(user)
            await session.flush()

            course = Course(
                slug="subscription_lock_test",
                title="Subscription lock test",
                requires_subscription=True,
                is_active=True,
            )

            session.add(course)
            await session.flush()

            subscription = Subscription(
                user_id=user.id,
                course_id=course.id,
                status="active",
                starts_at=now,
                ends_at=initial_ends_at,
            )

            session.add(subscription)
            await session.commit()

            user_id = user.id
            course_id = course.id

        async def extend_once() -> None:
            async with session_factory() as session:
                await (
                    activate_or_extend_subscription_in_session(
                        session=session,
                        user_id=user_id,
                        course_id=course_id,
                        days=30,
                    )
                )

                await session.commit()

        await asyncio.gather(
            extend_once(),
            extend_once(),
        )

        async with session_factory() as session:
            statement = select(
                Subscription
            ).where(
                Subscription.user_id == user_id,
                Subscription.course_id == course_id,
            )

            result = await session.execute(
                statement
            )

            stored_subscription = (
                result.scalar_one()
            )

            expected_ends_at = (
                initial_ends_at
                + timedelta(days=60)
            )

            assert (
                stored_subscription.status
                == "active"
            )

            assert (
                stored_subscription.ends_at
                == expected_ends_at
            )

    finally:
        await engine.dispose()