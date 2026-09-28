from uuid import uuid4

import pytest

from app.database.models.course import Course
from app.database.models.user import User
from app.database.session import (
    async_session_factory,
)
from app.services.user_service import (
    clear_current_course,
    get_current_course_slug,
    is_current_course,
    set_current_course,
)


@pytest.mark.asyncio
async def test_current_course_is_persisted():
    suffix = uuid4().hex[:12]

    telegram_id = (
        8_100_000_000_000
        + uuid4().int % 1_000_000_000_000
    )

    course_slug = (
        f"current_course_{suffix}"
    )

    async with async_session_factory() as session:
        user = User(
            telegram_id=telegram_id,
            username=f"user_{suffix}",
            first_name="Test",
        )

        course = Course(
            slug=course_slug,
            title="Current Course",
            requires_subscription=False,
            is_active=True,
        )

        session.add_all(
            [
                user,
                course,
            ]
        )

        await session.commit()

    assert (
        await get_current_course_slug(
            telegram_id
        )
        is None
    )

    selected = await set_current_course(
        telegram_id=telegram_id,
        course_slug=course_slug,
    )

    assert selected is True

    assert (
        await get_current_course_slug(
            telegram_id
        )
        == course_slug
    )

    assert (
        await is_current_course(
            telegram_id=telegram_id,
            course_slug=course_slug,
        )
        is True
    )

    cleared = await clear_current_course(
        telegram_id
    )

    assert cleared is True

    assert (
        await get_current_course_slug(
            telegram_id
        )
        is None
    )