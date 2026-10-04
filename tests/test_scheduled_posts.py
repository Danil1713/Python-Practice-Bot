import asyncio
import os
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.bot.handlers import admin_posts
from app.database.models.course import Course
from app.database.models.scheduled_post import (
    ScheduledPost,
)
from app.database.repositories.scheduled_post_repository import (
    ScheduledPostRepository,
)
from app.scheduler.publishing import (
    recover_stuck_publications,
)
from app.services.schedule_service import (
    ScheduleError,
    cancel_scheduled_post,
    publish_post_now,
)


@pytest.mark.asyncio
async def test_scheduled_post_can_be_claimed_only_once():
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
                scheduled_at=(datetime.now(timezone.utc) - timedelta(minutes=1)),
                status="scheduled",
            )

            session.add(post)
            await session.commit()

            post_id = post.id

        async def claim_post() -> bool:
            async with session_factory() as session:
                repository = ScheduledPostRepository(session)

                claimed = await repository.claim_scheduled(post_id)

                await session.commit()

                return claimed

        first_result, second_result = await asyncio.gather(
            claim_post(),
            claim_post(),
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
            statement = select(ScheduledPost).where(ScheduledPost.id == post_id)

            result = await session.execute(statement)

            stored_post = result.scalar_one()

            assert stored_post.status == "publishing"

            assert stored_post.publishing_started_at is not None

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_publish_now_does_not_report_success_when_telegram_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    channel_id = -1001234567890

    try:
        async with session_factory() as session:
            course = Course(
                slug="publish_now_failure_test",
                title="Publish now failure test",
                telegram_channel_id=channel_id,
                requires_subscription=False,
                is_active=True,
            )

            session.add(course)
            await session.flush()

            post = ScheduledPost(
                course_id=course.id,
                post_type="regular",
                content="Test publication",
                scheduled_at=(datetime.now(timezone.utc) + timedelta(hours=1)),
                status="scheduled",
            )

            session.add(post)
            await session.commit()

            post_id = post.id

        admin_id = 900000099

        monkeypatch.setattr(
            "app.services.publishing_service.get_admin_telegram_ids",
            lambda: {admin_id},
        )

        bot = AsyncMock()

        async def send_message(
            *,
            chat_id: int,
            text: str,
            reply_markup=None,
        ) -> None:
            if chat_id == channel_id:
                raise RuntimeError("Telegram unavailable")

        bot.send_message.side_effect = send_message

        with pytest.raises(
            ScheduleError,
            match=("Публикация не была отправлена"),
        ):
            await publish_post_now(
                post_id=post_id,
                bot=bot,
            )

        assert bot.send_message.await_count == 2

        channel_request = bot.send_message.await_args_list[0]
        admin_request = bot.send_message.await_args_list[1]

        assert channel_request.kwargs == {
            "chat_id": channel_id,
            "text": "Test publication",
        }

        assert admin_request.kwargs["chat_id"] == admin_id
        assert "Ошибка публикации" in admin_request.kwargs["text"]
        assert f"#{post_id}" in admin_request.kwargs["text"]
        assert "приостановлены" in admin_request.kwargs["text"]

        dismiss_button = admin_request.kwargs["reply_markup"].inline_keyboard[0][0]

        assert dismiss_button.text == "Скрыть"
        assert dismiss_button.callback_data == "notification:dismiss"

        async with session_factory() as session:
            statement = select(ScheduledPost).where(ScheduledPost.id == post_id)

            result = await session.execute(statement)

            stored_post = result.scalar_one()

            assert stored_post.status == "failed"

            assert stored_post.publishing_started_at is None

            assert stored_post.error_message == "Telegram unavailable"

            assert stored_post.published_at is None

            assert stored_post.telegram_message_id is None

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_failed_post_blocks_only_its_course():
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    now = datetime.now(timezone.utc)

    try:
        async with session_factory() as session:
            blocked_course = Course(
                slug="blocked_publication_course",
                title="Blocked publication course",
                requires_subscription=False,
                is_active=True,
            )

            other_course = Course(
                slug="unblocked_publication_course",
                title="Unblocked publication course",
                requires_subscription=False,
                is_active=True,
            )

            session.add_all(
                [
                    blocked_course,
                    other_course,
                ]
            )

            await session.flush()

            failed_post = ScheduledPost(
                course_id=blocked_course.id,
                post_type="regular",
                content="Failed publication",
                scheduled_at=(now - timedelta(minutes=2)),
                status="failed",
                error_message="Telegram unavailable",
            )

            blocked_post = ScheduledPost(
                course_id=blocked_course.id,
                post_type="regular",
                content="Must wait",
                scheduled_at=(now - timedelta(minutes=1)),
                status="scheduled",
            )

            other_post = ScheduledPost(
                course_id=other_course.id,
                post_type="regular",
                content="May continue",
                scheduled_at=(now - timedelta(minutes=1)),
                status="scheduled",
            )

            session.add_all(
                [
                    failed_post,
                    blocked_post,
                    other_post,
                ]
            )

            await session.commit()

            blocked_post_id = blocked_post.id
            other_post_id = other_post.id

        async with session_factory() as session:
            repository = ScheduledPostRepository(session)

            blocked_claim = await repository.claim_scheduled(blocked_post_id)

            other_claim = await repository.claim_scheduled(other_post_id)

            await session.commit()

        assert blocked_claim is False
        assert other_claim is True

        async with session_factory() as session:
            statement = select(ScheduledPost).where(
                ScheduledPost.id.in_(
                    [
                        blocked_post_id,
                        other_post_id,
                    ]
                )
            )

            result = await session.execute(statement)

            posts = {post.id: post for post in result.scalars().all()}

            assert posts[blocked_post_id].status == "scheduled"
            assert posts[other_post_id].status == "publishing"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cancelling_failed_post_unblocks_course():
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    now = datetime.now(timezone.utc)

    try:
        async with session_factory() as session:
            course = Course(
                slug="cancel_failed_publication_course",
                title="Cancel failed publication course",
                requires_subscription=False,
                is_active=True,
            )

            session.add(course)
            await session.flush()

            failed_post = ScheduledPost(
                course_id=course.id,
                post_type="regular",
                content="Failed publication",
                scheduled_at=(now - timedelta(minutes=2)),
                status="failed",
                error_message="Telegram unavailable",
            )

            next_post = ScheduledPost(
                course_id=course.id,
                post_type="regular",
                content="Next publication",
                scheduled_at=(now - timedelta(minutes=1)),
                status="scheduled",
            )

            session.add_all(
                [
                    failed_post,
                    next_post,
                ]
            )
            await session.commit()

            failed_post_id = failed_post.id
            next_post_id = next_post.id

        await cancel_scheduled_post(failed_post_id)

        async with session_factory() as session:
            repository = ScheduledPostRepository(session)

            cancelled_post = await repository.get_by_id(failed_post_id)

            next_post_claimed = await repository.claim_scheduled(next_post_id)

            await session.commit()

            assert cancelled_post is not None
            assert cancelled_post.status == "cancelled"
            assert next_post_claimed is True

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_stuck_publication_notifies_admin(
    monkeypatch: pytest.MonkeyPatch,
):
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    now = datetime.now(timezone.utc)
    admin_id = 900000099

    try:
        async with session_factory() as session:
            course = Course(
                slug="stuck_publication_course",
                title="Stuck publication course",
                requires_subscription=False,
                is_active=True,
            )

            session.add(course)
            await session.flush()

            post = ScheduledPost(
                course_id=course.id,
                post_type="regular",
                content="Possibly published content",
                scheduled_at=(now - timedelta(minutes=10)),
                status="publishing",
                publishing_started_at=(now - timedelta(minutes=10)),
            )

            session.add(post)
            await session.commit()

            post_id = post.id

        monkeypatch.setattr(
            "app.services.publishing_service.get_admin_telegram_ids",
            lambda: {admin_id},
        )

        bot = AsyncMock()

        recovered_count = await recover_stuck_publications(
            bot=bot,
            before=(now - timedelta(minutes=5)),
        )

        assert recovered_count == 1
        assert bot.send_message.await_count == 1

        notification = bot.send_message.await_args

        assert notification.kwargs["chat_id"] == admin_id
        assert f"#{post_id}" in notification.kwargs["text"]
        assert "приостановлены" in notification.kwargs["text"]

        dismiss_button = notification.kwargs["reply_markup"].inline_keyboard[0][0]

        assert dismiss_button.text == "Скрыть"
        assert dismiss_button.callback_data == "notification:dismiss"

        async with session_factory() as session:
            repository = ScheduledPostRepository(session)

            stored_post = await repository.get_by_id(post_id)

            assert stored_post is not None
            assert stored_post.status == "failed"
            assert stored_post.publishing_started_at is None
            assert stored_post.error_message is not None
            assert "Проверь Telegram-канал" in (stored_post.error_message)

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_publish_now_requires_confirmation(
    monkeypatch: pytest.MonkeyPatch,
):
    check_admin = AsyncMock(return_value=True)

    get_post = AsyncMock(
        return_value=SimpleNamespace(
            id=123,
            status="scheduled",
            post_type="regular",
        )
    )

    publish_post_now = AsyncMock()

    monkeypatch.setattr(
        admin_posts,
        "check_admin",
        check_admin,
    )

    monkeypatch.setattr(
        admin_posts,
        "get_admin_post_for_course",
        get_post,
    )

    monkeypatch.setattr(
        admin_posts,
        "publish_post_now",
        publish_post_now,
    )

    callback = AsyncMock()
    callback.data = "admin:publish:123:demo"

    await admin_posts.admin_publish_now_handler(callback)

    publish_post_now.assert_not_awaited()

    callback.message.edit_text.assert_awaited_once()

    edit_request = callback.message.edit_text.await_args

    keyboard = edit_request.kwargs["reply_markup"]

    confirm_button = keyboard.inline_keyboard[0][0]
    back_button = keyboard.inline_keyboard[1][0]

    assert confirm_button.text == "✅ Да, опубликовать"
    assert confirm_button.callback_data == "admin:publish:confirm:123:demo"

    assert back_button.text == "⬅️ Нет, вернуться"
    assert back_button.callback_data == "admin:post:123:demo"


@pytest.mark.asyncio
async def test_invalid_reschedule_datetime_explains_retry(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        admin_posts,
        "is_admin",
        lambda user_id: True,
    )

    state = SimpleNamespace(
        data={
            "post_id": 123,
            "course_slug": "demo",
        },
        current_state=(admin_posts.AdminScheduleStates.waiting_for_reschedule_datetime),
    )

    async def get_data():
        return dict(state.data)

    async def clear():
        state.data.clear()
        state.current_state = None

    state.get_data = get_data
    state.clear = clear

    message = SimpleNamespace(
        from_user=SimpleNamespace(id=1),
        text="завтра вечером",
        answer=AsyncMock(),
    )

    await admin_posts.admin_reschedule_datetime_handler(
        message,
        state,
    )

    assert state.current_state == (
        admin_posts.AdminScheduleStates.waiting_for_reschedule_datetime
    )

    answer = message.answer.await_args

    assert "Неверный формат" in answer.kwargs["text"]
    assert "Попробуй ещё раз" in answer.kwargs["text"]
    assert "Бот продолжает ждать" in (answer.kwargs["text"])
