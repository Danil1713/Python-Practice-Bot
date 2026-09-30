from datetime import UTC, datetime

from app.database.models.user import User
from app.database.repositories.course_repository import CourseRepository
from app.database.repositories.user_repository import UserRepository
from app.database.session import async_session_factory

AI_REVIEW_CONSENT_VERSION = "v1"


async def register_or_update_user(
    telegram_id: int,
    username: str | None,
    first_name: str,
) -> User:
    async with async_session_factory() as session:
        repository = UserRepository(session)

        user = await repository.upsert_telegram_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )

        await session.commit()

        return user


async def has_current_ai_review_consent(
    telegram_id: int,
) -> bool:
    async with async_session_factory() as session:
        repository = UserRepository(session)

        user = await repository.get_by_telegram_id(telegram_id)

        if user is None:
            return False

        return (
            user.ai_review_consent_version == AI_REVIEW_CONSENT_VERSION
            and user.ai_review_consent_at is not None
        )


async def accept_ai_review_consent(
    telegram_id: int,
) -> bool:
    async with async_session_factory() as session:
        repository = UserRepository(session)

        accepted = await repository.set_ai_review_consent(
            telegram_id=telegram_id,
            version=(AI_REVIEW_CONSENT_VERSION),
            accepted_at=datetime.now(UTC),
        )

        if not accepted:
            await session.rollback()
            return False

        await session.commit()

        return True


async def set_current_course(
    *,
    telegram_id: int,
    course_slug: str,
) -> bool:
    async with async_session_factory() as session:
        user_repository = UserRepository(session)
        course_repository = CourseRepository(session)

        course = await course_repository.get_by_slug(course_slug)

        if course is None:
            return False

        updated = await user_repository.set_current_course_id(
            telegram_id=telegram_id,
            course_id=course.id,
        )

        if not updated:
            await session.rollback()
            return False

        await session.commit()

        return True


async def clear_current_course(
    telegram_id: int,
) -> bool:
    async with async_session_factory() as session:
        repository = UserRepository(session)

        updated = await repository.set_current_course_id(
            telegram_id=telegram_id,
            course_id=None,
        )

        if not updated:
            await session.rollback()
            return False

        await session.commit()

        return True


async def get_current_course_slug(
    telegram_id: int,
) -> str | None:
    async with async_session_factory() as session:
        user_repository = UserRepository(session)
        course_repository = CourseRepository(session)

        user = await user_repository.get_by_telegram_id(telegram_id)

        if user is None or user.current_course_id is None:
            return None

        course = await course_repository.get_by_id(user.current_course_id)

        if course is None or not course.is_active:
            return None

        return course.slug


async def is_current_course(
    *,
    telegram_id: int,
    course_slug: str,
) -> bool:
    current_course_slug = await get_current_course_slug(telegram_id)

    return current_course_slug == course_slug
