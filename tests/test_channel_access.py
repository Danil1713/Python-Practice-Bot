import asyncio
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.bot.handlers.channel_access import (
    course_join_request_handler,
)
from app.bot.keyboards.subscription import (
    get_channel_join_keyboard,
)
from app.database.models.course import Course
from app.database.models.subscription import (
    Subscription,
)
from app.database.models.subscription_event import (
    SubscriptionEvent,
)
from app.database.models.user import User
from app.database.session import (
    async_session_factory,
)
from app.services.channel_access_service import (
    ChannelAccessError,
    create_course_join_request_link,
    get_expired_active_subscription_ids,
    revoke_expired_subscription_access,
)
from app.services.subscription_service import (
    activate_or_extend_subscription_in_session,
)


def test_free_channel_join_keyboard_returns_to_menu():
    keyboard = get_channel_join_keyboard(
        invite_link="https://t.me/+demo",
        course_slug="demo",
        requires_subscription=False,
    )

    back_button = keyboard.inline_keyboard[1][0]

    assert back_button.text == "⬅️ Назад к меню"
    assert back_button.callback_data == "nav:menu:demo"


def test_paid_channel_join_keyboard_returns_to_subscription():
    keyboard = get_channel_join_keyboard(
        invite_link="https://t.me/+python-start",
        course_slug="python_start",
        requires_subscription=True,
    )

    back_button = keyboard.inline_keyboard[1][0]

    assert back_button.text == "⬅️ Назад к подписке"
    assert back_button.callback_data == "menu:subscription:python_start"


async def create_channel_access_data(
    *,
    expired: bool,
    with_subscription: bool = True,
):
    suffix = uuid4().hex[:12]

    telegram_id = 8_200_000_000_000 + uuid4().int % 1_000_000_000_000

    channel_id = -(1_000_000_000_000 + uuid4().int % 1_000_000_000)

    now = datetime.now(timezone.utc)

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
                starts_at = now - timedelta(days=2)

                ends_at = now - timedelta(days=1)

            else:
                starts_at = now

                ends_at = now + timedelta(days=30)

            subscription = Subscription(
                user_id=user.id,
                course_id=course.id,
                status="active",
                starts_at=starts_at,
                ends_at=ends_at,
            )

            session.add(subscription)

            await session.flush()

        await session.commit()

        return (
            telegram_id,
            course.slug,
            channel_id,
            (subscription.id if subscription is not None else None),
        )


@pytest.mark.asyncio
async def test_active_subscription_gets_join_link():
    (
        telegram_id,
        course_slug,
        channel_id,
        _,
    ) = await create_channel_access_data(expired=False)

    bot = AsyncMock()

    bot.unban_chat_member.return_value = True

    bot.create_chat_invite_link.return_value = SimpleNamespace(
        invite_link=("https://t.me/+test-link")
    )

    link = await create_course_join_request_link(
        bot=bot,
        telegram_user_id=telegram_id,
        course_slug=course_slug,
    )

    assert link == ("https://t.me/+test-link")

    bot.unban_chat_member.assert_awaited_once_with(
        chat_id=channel_id,
        user_id=telegram_id,
        only_if_banned=True,
    )

    call = bot.create_chat_invite_link.await_args

    assert call.kwargs["chat_id"] == channel_id

    assert call.kwargs["creates_join_request"] is True


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
    ) = await create_channel_access_data(expired=True)

    assert subscription_id is not None

    bot = AsyncMock()

    bot.ban_chat_member.return_value = True
    bot.unban_chat_member.return_value = True

    revoked = await revoke_expired_subscription_access(
        subscription_id=subscription_id,
        bot=bot,
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

    bot.send_message.assert_awaited_once()

    notification = bot.send_message.await_args

    assert notification.kwargs["chat_id"] == telegram_id
    assert "Подписка закончилась" in (notification.kwargs["text"])
    assert "Channel Access" in notification.kwargs["text"]

    dismiss_button = notification.kwargs["reply_markup"].inline_keyboard[0][0]

    assert dismiss_button.text == "Скрыть"
    assert dismiss_button.callback_data == "notification:dismiss"

    async with async_session_factory() as session:
        subscription = await session.get(
            Subscription,
            subscription_id,
        )

        assert subscription is not None

        assert subscription.status == "cancelled"

        result = await session.execute(
            select(SubscriptionEvent).where(
                SubscriptionEvent.subscription_id == subscription_id
            )
        )

        event = result.scalar_one()

        assert event.actor_telegram_id is None
        assert event.event_type == "subscription_expired"
        assert event.source == "scheduler"
        assert event.reason == "subscription_expired"
        assert event.days is None
        assert event.old_status == "revoking"
        assert event.new_status == "cancelled"
        assert event.idempotency_key.startswith(f"expire:{subscription_id}:")


@pytest.mark.asyncio
async def test_active_user_join_request_is_approved():
    (
        telegram_id,
        _,
        channel_id,
        _,
    ) = await create_channel_access_data(expired=False)

    request = SimpleNamespace(
        chat=SimpleNamespace(id=channel_id),
        from_user=SimpleNamespace(id=telegram_id),
    )

    bot = AsyncMock()

    await course_join_request_handler(
        request=request,
        bot=bot,
    )

    bot.approve_chat_join_request.assert_awaited_once_with(
        chat_id=channel_id,
        user_id=telegram_id,
    )

    bot.decline_chat_join_request.assert_not_awaited()


@pytest.mark.asyncio
async def test_inactive_user_join_request_is_declined():
    (
        telegram_id,
        _,
        channel_id,
        _,
    ) = await create_channel_access_data(
        expired=False,
        with_subscription=False,
    )

    request = SimpleNamespace(
        chat=SimpleNamespace(id=channel_id),
        from_user=SimpleNamespace(id=telegram_id),
    )

    bot = AsyncMock()

    await course_join_request_handler(
        request=request,
        bot=bot,
    )

    bot.decline_chat_join_request.assert_awaited_once_with(
        chat_id=channel_id,
        user_id=telegram_id,
    )

    bot.approve_chat_join_request.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_channel_revocation_restores_active_status():
    (
        _,
        _,
        _,
        subscription_id,
    ) = await create_channel_access_data(expired=True)

    assert subscription_id is not None

    bot = AsyncMock()

    bot.ban_chat_member.side_effect = RuntimeError("Telegram unavailable")

    with pytest.raises(
        ChannelAccessError,
        match="Не удалось отозвать доступ",
    ):
        await revoke_expired_subscription_access(
            subscription_id=subscription_id,
            bot=bot,
        )

    async with async_session_factory() as session:
        subscription = await session.get(
            Subscription,
            subscription_id,
        )

        assert subscription is not None
        assert subscription.status == "active"


@pytest.mark.asyncio
async def test_stale_revoking_subscription_is_recovered():
    (
        _,
        _,
        _,
        subscription_id,
    ) = await create_channel_access_data(expired=True)

    assert subscription_id is not None

    async with async_session_factory() as session:
        subscription = await session.get(
            Subscription,
            subscription_id,
        )

        assert subscription is not None

        subscription.status = "revoking"
        subscription.updated_at = datetime.now(timezone.utc) - timedelta(minutes=20)

        await session.commit()

    candidates = await get_expired_active_subscription_ids()

    assert subscription_id in candidates


@pytest.mark.asyncio
async def test_subscription_can_be_renewed_during_telegram_revocation():
    (
        telegram_id,
        _,
        _,
        subscription_id,
    ) = await create_channel_access_data(expired=True)

    assert subscription_id is not None

    async with async_session_factory() as session:
        subscription = await session.get(
            Subscription,
            subscription_id,
        )

        assert subscription is not None

        user_id = subscription.user_id
        course_id = subscription.course_id

    telegram_started = asyncio.Event()
    allow_telegram_to_finish = asyncio.Event()

    async def delayed_ban(
        **_,
    ) -> bool:
        telegram_started.set()

        await allow_telegram_to_finish.wait()

        return True

    bot = AsyncMock()

    bot.ban_chat_member.side_effect = delayed_ban
    bot.unban_chat_member.return_value = True

    bot.create_chat_invite_link.return_value = SimpleNamespace(
        invite_link="https://t.me/+renewed"
    )

    revoke_task = asyncio.create_task(
        revoke_expired_subscription_access(
            subscription_id=subscription_id,
            bot=bot,
        )
    )

    await asyncio.wait_for(
        telegram_started.wait(),
        timeout=2,
    )

    async def renew_subscription() -> None:
        async with async_session_factory() as session:
            await activate_or_extend_subscription_in_session(
                session=session,
                user_id=user_id,
                course_id=course_id,
                days=30,
            )

            await session.commit()

    try:
        await asyncio.wait_for(
            renew_subscription(),
            timeout=2,
        )

    finally:
        allow_telegram_to_finish.set()

    revoked = await asyncio.wait_for(
        revoke_task,
        timeout=2,
    )

    assert revoked is False

    async with async_session_factory() as session:
        subscription = await session.get(
            Subscription,
            subscription_id,
        )

        assert subscription is not None
        assert subscription.status == "active"
        assert subscription.ends_at > datetime.now(timezone.utc)

    bot.send_message.assert_awaited_once()

    sent_message = bot.send_message.await_args

    assert sent_message.kwargs["chat_id"] == telegram_id
