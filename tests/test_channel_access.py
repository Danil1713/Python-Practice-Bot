from datetime import (
    datetime,
    timedelta,
    timezone,
)
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.database.models.course import Course
from app.database.models.subscription import (
    Subscription,
)
from app.database.models.user import User
from app.database.session import (
    async_session_factory,
)
from app.services.channel_access_service import (
    ChannelAccessError,
    create_course_join_request_link,
    revoke_expired_subscription_access,
)


async def create_channel_access_data(
    *,
    expired: bool,
    with_subscription: bool = True,
):
    suffix = uuid4().hex[:12]

    telegram_id = (
        8_200_000_000_000
        + uuid4().int % 1_000_000_000_000
    )

    channel_id = -(
        1_000_000_000_000
        + uuid4().int % 1_000_000_000
    )

    now = datetime.now(
        timezone.utc
    )

    async with async_session_factory() as session:
        user = User(
            telegram_id=telegram_id,
            username=f"channel_{suffix}",
            first_name="Channel Test",
        )

        course = Course(
            slug=f"channel_{suffix}",
            title="Channel Access",
            telegram_channel_id=channel_id,
            requires_subscription=True,
            is_active=True,
        )

        session.add_all(
            [
                user,
                course,
            ]
        )

        await session.flush()

        subscription = None

        if with_subscription:
            if expired:
                starts_at = (
                    now
                    - timedelta(days=2)
                )

                ends_at = (
                    now
                    - timedelta(days=1)
                )

            else:
                starts_at = now

                ends_at = (
                    now
                    + timedelta(days=30)
                )

            subscription = Subscription(
                user_id=user.id,
                course_id=course.id,
                status="active",
                starts_at=starts_at,
                ends_at=ends_at,
            )

            session.add(
                subscription
            )

            await session.flush()

        await session.commit()

        return (
            telegram_id,
            course.slug,
            channel_id,
            (
                subscription.id
                if subscription is not None
                else None
            ),
        )


@pytest.mark.asyncio
async def test_active_subscription_gets_join_link():
    (
        telegram_id,
        course_slug,
        channel_id,
        _,
    ) = await create_channel_access_data(
        expired=False
    )

    bot = AsyncMock()

    bot.unban_chat_member.return_value = True

    bot.create_chat_invite_link.return_value = (
        SimpleNamespace(
            invite_link=(
                "https://t.me/+test-link"
            )
        )
    )

    link = await create_course_join_request_link(
        bot=bot,
        telegram_user_id=telegram_id,
        course_slug=course_slug,
    )

    assert link == (
        "https://t.me/+test-link"
    )

    bot.unban_chat_member.assert_awaited_once_with(
        chat_id=channel_id,
        user_id=telegram_id,
        only_if_banned=True,
    )

    call = (
        bot.create_chat_invite_link.await_args
    )

    assert (
        call.kwargs["chat_id"]
        == channel_id
    )

    assert (
        call.kwargs[
            "creates_join_request"
        ]
        is True
    )


@pytest.mark.asyncio
async def test_inactive_user_cannot_get_join_link():
    (
        telegram_id,
        course_slug,
        _,
        _,
    ) = await create_channel_access_data(
        expired=False,
        with_subscription=False,
    )

    bot = AsyncMock()

    with pytest.raises(
        ChannelAccessError,
        match="активная подписка",
    ):
        await create_course_join_request_link(
            bot=bot,
            telegram_user_id=telegram_id,
            course_slug=course_slug,
        )

    bot.create_chat_invite_link.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_subscription_revokes_channel():
    (
        telegram_id,
        _,
        channel_id,
        subscription_id,
    ) = await create_channel_access_data(
        expired=True
    )

    assert subscription_id is not None

    bot = AsyncMock()

    bot.ban_chat_member.return_value = True
    bot.unban_chat_member.return_value = True

    revoked = (
        await revoke_expired_subscription_access(
            subscription_id=subscription_id,
            bot=bot,
        )
    )

    assert revoked is True

    bot.ban_chat_member.assert_awaited_once_with(
        chat_id=channel_id,
        user_id=telegram_id,
    )

    bot.unban_chat_member.assert_awaited_once_with(
        chat_id=channel_id,
        user_id=telegram_id,
        only_if_banned=True,
    )

    async with async_session_factory() as session:
        subscription = await session.get(
            Subscription,
            subscription_id,
        )

        assert subscription is not None

        assert (
            subscription.status
            == "cancelled"
        )