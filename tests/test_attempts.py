import asyncio
import os
from datetime import datetime, timedelta, timezone

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
from app.services.attempt_service import (
    get_attempt_detail,
)


@pytest.mark.asyncio
async def test_pending_attempt_can_be_claimed_only_once():
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

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
                source_code=("print('test')"),
                status="pending",
                xp_snapshot=100,
            )

            session.add(attempt)
            await session.commit()

            attempt_id = attempt.id

        async def claim_attempt() -> bool:
            async with session_factory() as session:
                repository = AttemptRepository(session)

                claimed = await repository.claim_pending(attempt_id)

                await session.commit()

                return claimed

        first_result, second_result = await asyncio.gather(
            claim_attempt(),
            claim_attempt(),
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
            statement = select(Attempt).where(Attempt.id == attempt_id)

            result = await session.execute(statement)

            stored_attempt = result.scalar_one()

            assert stored_attempt.status == "checking"

            assert stored_attempt.checking_started_at is not None

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pending_attempt_is_not_available_until_status_message_saved():
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            course = Course(
                slug="pending_status_message_test",
                title="Pending status message test",
                requires_subscription=False,
                is_active=True,
            )

            session.add(course)
            await session.flush()

            user = User(
                telegram_id=900000002,
                username="pending_status_test_user",
                first_name="Test",
            )

            session.add(user)
            await session.flush()

            project = Project(
                course_id=course.id,
                number=1,
                title="Pending status message project",
                max_xp=100,
            )

            session.add(project)
            await session.flush()

            attempt = Attempt(
                user_id=user.id,
                project_id=project.id,
                attempt_number=1,
                filename="solution.py",
                source_code="print('test')",
                status="pending",
                xp_snapshot=100,
            )

            session.add(attempt)
            await session.commit()

            attempt_id = attempt.id

        async with session_factory() as session:
            repository = AttemptRepository(session)

            pending = await repository.get_pending()

            assert all(item.id != attempt_id for item in pending)

        async with session_factory() as session:
            repository = AttemptRepository(session)

            attempt = await repository.get_by_id(attempt_id)

            assert attempt is not None

            await repository.set_status_message(
                attempt=attempt,
                chat_id=900000002,
                message_id=12345,
            )

            await session.commit()

        async with session_factory() as session:
            repository = AttemptRepository(session)

            pending = await repository.get_pending()

            assert any(item.id == attempt_id for item in pending)

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_stuck_pending_attempt_without_status_message_is_recovered():
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            course = Course(
                slug="stuck_pending_setup_test",
                title="Stuck pending setup test",
                requires_subscription=False,
                is_active=True,
            )

            session.add(course)
            await session.flush()

            user = User(
                telegram_id=900000003,
                username="stuck_pending_user",
                first_name="Test",
            )

            session.add(user)
            await session.flush()

            project = Project(
                course_id=course.id,
                number=1,
                title="Stuck pending project",
                max_xp=100,
            )

            session.add(project)
            await session.flush()

            attempt = Attempt(
                user_id=user.id,
                project_id=project.id,
                attempt_number=1,
                filename="solution.py",
                source_code="print('test')",
                status="pending",
                xp_snapshot=100,
                submitted_at=(datetime.now(timezone.utc) - timedelta(minutes=10)),
            )

            session.add(attempt)
            await session.commit()

            attempt_id = attempt.id

        async with session_factory() as session:
            repository = AttemptRepository(session)

            recovered = await repository.recover_stuck_pending_setup(
                before=(datetime.now(timezone.utc) - timedelta(minutes=2))
            )

            await session.commit()

            assert recovered == 1

        async with session_factory() as session:
            repository = AttemptRepository(session)

            attempt = await repository.get_by_id(attempt_id)

            assert attempt is not None
            assert attempt.status == "error"
            assert attempt.checked_at is not None
            assert attempt.error_message == (
                "Не удалось подготовить Telegram-сообщение для результата проверки."
            )

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_attempt_detail_contains_course_slug():
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            course = Course(
                slug="attempt_detail_course",
                title="Attempt detail course",
                requires_subscription=False,
                is_active=True,
            )

            session.add(course)
            await session.flush()

            user = User(
                telegram_id=900000004,
                username="attempt_detail_user",
                first_name="Test",
            )

            session.add(user)
            await session.flush()

            project = Project(
                course_id=course.id,
                number=1,
                title="Attempt detail project",
                max_xp=100,
            )

            session.add(project)
            await session.flush()

            attempt = Attempt(
                user_id=user.id,
                project_id=project.id,
                attempt_number=1,
                filename="solution.py",
                source_code="print('test')",
                status="passed",
                xp_snapshot=100,
            )

            session.add(attempt)
            await session.commit()

            attempt_id = attempt.id
            telegram_id = user.telegram_id

        detail = await get_attempt_detail(
            telegram_user_id=telegram_id,
            attempt_id=attempt_id,
        )

        assert detail is not None
        assert detail.course_slug == "attempt_detail_course"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_ai_check_limit_ignores_provider_errors():
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            course = Course(
                slug="ai_limit_provider_error_course",
                title="AI limit provider error course",
                requires_subscription=False,
                is_active=True,
            )

            session.add(course)
            await session.flush()

            user = User(
                telegram_id=900000005,
                username="ai_limit_provider_error_user",
                first_name="Test",
            )

            session.add(user)
            await session.flush()

            project = Project(
                course_id=course.id,
                number=1,
                title="AI limit provider error project",
                max_xp=100,
            )

            session.add(project)
            await session.flush()

            completed_ai_attempt = Attempt(
                user_id=user.id,
                project_id=project.id,
                attempt_number=1,
                filename="completed.py",
                source_code="print('completed')",
                status="failed",
                xp_snapshot=100,
                ai_model="test-model",
                ai_result_json='{"verdict":"failed"}',
            )

            provider_error_attempt = Attempt(
                user_id=user.id,
                project_id=project.id,
                attempt_number=2,
                filename="provider_error.py",
                source_code="print('provider error')",
                status="error",
                xp_snapshot=100,
                ai_model="test-model",
                error_message="AI provider unavailable",
            )

            local_check_attempt = Attempt(
                user_id=user.id,
                project_id=project.id,
                attempt_number=3,
                filename="local_check.py",
                source_code="invalid syntax",
                status="failed",
                xp_snapshot=100,
                ai_model=None,
            )

            session.add_all(
                [
                    completed_ai_attempt,
                    provider_error_attempt,
                    local_check_attempt,
                ]
            )
            await session.commit()

            repository = AttemptRepository(session)

            used = await repository.count_ai_checks(
                user_id=user.id,
                project_id=project.id,
            )

            assert used == 1

    finally:
        await engine.dispose()
