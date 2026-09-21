import asyncio
import os

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.models.attempt import Attempt
from app.database.models.course import Course
from app.database.models.project import Project
from app.database.models.user import User
from app.database.repositories.attempt_repository import (
    AttemptRepository,
)


@pytest.mark.asyncio
async def test_pending_attempt_can_be_claimed_only_once():
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
                slug="claim_test_course",
                title="Claim test course",
                requires_subscription=False,
                is_active=True,
            )

            session.add(course)
            await session.flush()

            user = User(
                telegram_id=900000001,
                username="claim_test_user",
                first_name="Test",
            )

            session.add(user)
            await session.flush()

            project = Project(
                course_id=course.id,
                number=1,
                title="Claim test project",
                max_xp=100,
            )

            session.add(project)
            await session.flush()

            attempt = Attempt(
                user_id=user.id,
                project_id=project.id,
                attempt_number=1,
                filename="solution.py",
                source_code=(
                    "print('test')"
                ),
                status="pending",
                xp_snapshot=100,
            )

            session.add(attempt)
            await session.commit()

            attempt_id = attempt.id

        async def claim_attempt() -> bool:
            async with session_factory() as session:
                repository = AttemptRepository(
                    session
                )

                claimed = (
                    await repository.claim_pending(
                        attempt_id
                    )
                )

                await session.commit()

                return claimed

        first_result, second_result = (
            await asyncio.gather(
                claim_attempt(),
                claim_attempt(),
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
                Attempt
            ).where(
                Attempt.id == attempt_id
            )

            result = await session.execute(
                statement
            )

            stored_attempt = (
                result.scalar_one()
            )

            assert (
                stored_attempt.status
                == "checking"
            )

            assert (
                stored_attempt.checking_started_at
                is not None
            )

    finally:
        await engine.dispose()