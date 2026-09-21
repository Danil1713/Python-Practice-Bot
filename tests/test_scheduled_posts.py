import asyncio
import os
from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.models.course import Course
from app.database.models.scheduled_post import (
    ScheduledPost,
)
from app.database.repositories.scheduled_post_repository import (
    ScheduledPostRepository,
)


@pytest.mark.asyncio
async def test_scheduled_post_can_be_claimed_only_once():
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
            course = Course(
                slug="scheduled_claim_test",
                title="Scheduled claim test",
                requires_subscription=False,
                is_active=True,
            )

            session.add(course)
            await session.flush()

            post = ScheduledPost(
                course_id=course.id,
                post_type="regular",
                content="Test publication",
                scheduled_at=(
                    datetime.now(timezone.utc)
                    - timedelta(minutes=1)
                ),
                status="scheduled",
            )

            session.add(post)
            await session.commit()

            post_id = post.id

        async def claim_post() -> bool:
            async with session_factory() as session:
                repository = (
                    ScheduledPostRepository(
                        session
                    )
                )

                claimed = (
                    await repository
                    .claim_scheduled(
                        post_id
                    )
                )

                await session.commit()

                return claimed

        first_result, second_result = (
            await asyncio.gather(
                claim_post(),
                claim_post(),
            )
        )

        assert sorted(
            [
                first_result,
                second_result,
            ]
        ) == [
            False,
            True,
        ]

        async with session_factory() as session:
            statement = select(
                ScheduledPost
            ).where(
                ScheduledPost.id == post_id
            )

            result = await session.execute(
                statement
            )

            stored_post = (
                result.scalar_one()
            )

            assert (
                stored_post.status
                == "publishing"
            )

            assert (
                stored_post
                .publishing_started_at
                is not None
            )

    finally:
        await engine.dispose()