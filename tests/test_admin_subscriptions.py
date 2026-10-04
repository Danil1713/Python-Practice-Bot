import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
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

from app.bot.handlers import admin_subscriptions
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
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

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

        first_result = await activate_or_extend_subscription(
            user_id=user_id,
            course_id=course_id,
            days=30,
            actor_telegram_id=700000001,
            idempotency_key=operation_id,
        )

        second_result = await activate_or_extend_subscription(
            user_id=user_id,
            course_id=course_id,
            days=30,
            actor_telegram_id=700000001,
            idempotency_key=operation_id,
        )

        assert second_result.ends_at == first_result.ends_at

        assert first_result.telegram_user_id == 900000201
        assert first_result.course_title == "Admin audit course"

        assert second_result.telegram_user_id == 900000201
        assert second_result.course_title == "Admin audit course"

        async with session_factory() as session:
            event_count = await session.scalar(
                select(func.count(SubscriptionEvent.id)).where(
                    SubscriptionEvent.idempotency_key == operation_id
                )
            )

            subscription = await session.scalar(
                select(Subscription).where(
                    Subscription.user_id == user_id,
                    Subscription.course_id == course_id,
                )
            )

            event = await session.scalar(
                select(SubscriptionEvent).where(
                    SubscriptionEvent.idempotency_key == operation_id
                )
            )

            assert subscription is not None
            assert event is not None

            assert event_count == 1

            assert subscription.ends_at == first_result.ends_at

            assert event.actor_telegram_id == 700000001

            assert event.source == "admin"

            assert event.reason == "manual_admin_grant"

            assert event.days == 30

    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "expected_error"),
    [
        (
            "не число",
            "Введи целое число",
        ),
        (
            "0",
            "должно быть больше 0",
        ),
        (
            str(admin_subscriptions.MAX_ADMIN_SUBSCRIPTION_DAYS + 1),
            "Нельзя выдать подписку",
        ),
    ],
)
async def test_invalid_subscription_days_explain_retry(
    monkeypatch,
    text,
    expected_error,
):
    monkeypatch.setattr(
        admin_subscriptions,
        "is_admin",
        lambda user_id: True,
    )

    message = SimpleNamespace(
        from_user=SimpleNamespace(id=1),
        text=text,
        answer=AsyncMock(),
    )

    state = AsyncMock()

    await admin_subscriptions.admin_subscription_days_handler(
        message,
        state,
    )

    answer = message.answer.await_args

    assert expected_error in answer.kwargs["text"]
    assert "Попробуй ещё раз" in answer.kwargs["text"]
    assert "Бот продолжает ждать" in answer.kwargs["text"]

    state.clear.assert_not_awaited()
    state.update_data.assert_not_awaited()
    state.set_state.assert_not_awaited()
