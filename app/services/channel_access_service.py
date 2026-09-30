import logging
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from aiogram import Bot
from sqlalchemy import select

from app.database.models.subscription import (
    Subscription,
)
from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.subscription_repository import (
    SubscriptionRepository,
)
from app.database.repositories.user_repository import (
    UserRepository,
)
from app.database.session import (
    async_session_factory,
)

logger = logging.getLogger(__name__)

JOIN_LINK_LIFETIME_MINUTES = 15


class ChannelAccessError(Exception):
    pass


async def create_course_join_request_link(
    *,
    bot: Bot,
    telegram_user_id: int,
    course_slug: str,
) -> str:
    async with async_session_factory() as session:
        user_repository = UserRepository(session)
        course_repository = CourseRepository(session)
        subscription_repository = SubscriptionRepository(session)

        user = await user_repository.get_by_telegram_id(telegram_user_id)

        if user is None:
            raise ChannelAccessError("Пользователь не найден.")

        course = await course_repository.get_by_slug(course_slug)

        if course is None:
            raise ChannelAccessError("Курс не найден.")

        if course.telegram_channel_id is None:
            raise ChannelAccessError("Telegram-канал курса ещё не настроен.")

        if course.requires_subscription:
            subscription = await subscription_repository.get_active_subscription(
                user_id=user.id,
                course_id=course.id,
            )

            if subscription is None:
                raise ChannelAccessError(
                    "Для доступа к каналу нужна активная подписка."
                )

        channel_id = course.telegram_channel_id

    try:
        await bot.unban_chat_member(
            chat_id=channel_id,
            user_id=telegram_user_id,
            only_if_banned=True,
        )

        invite = await bot.create_chat_invite_link(
            chat_id=channel_id,
            expire_date=(
                datetime.now(timezone.utc)
                + timedelta(minutes=(JOIN_LINK_LIFETIME_MINUTES))
            ),
            creates_join_request=True,
        )

    except Exception as error:
        logger.exception(
            "Could not create channel access "
            "telegram_user_id=%s "
            "course_slug=%s "
            "channel_id=%s",
            telegram_user_id,
            course_slug,
            channel_id,
        )

        raise ChannelAccessError(
            "Не удалось подготовить доступ к Telegram-каналу."
        ) from error

    return invite.invite_link


async def get_course_by_channel_id(
    telegram_channel_id: int,
):
    async with async_session_factory() as session:
        repository = CourseRepository(session)

        return await repository.get_by_telegram_channel_id(telegram_channel_id)


async def get_expired_active_subscription_ids(
    *,
    limit: int = 50,
) -> list[int]:
    now = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        statement = (
            select(Subscription.id)
            .where(
                Subscription.status == "active",
                Subscription.ends_at <= now,
            )
            .order_by(Subscription.ends_at.asc())
            .limit(limit)
        )

        result = await session.execute(statement)

        return list(result.scalars().all())


async def revoke_expired_subscription_access(
    *,
    subscription_id: int,
    bot: Bot,
) -> bool:
    async with async_session_factory() as session:
        statement = (
            select(Subscription)
            .where(Subscription.id == subscription_id)
            .with_for_update()
        )

        result = await session.execute(statement)

        subscription = result.scalar_one_or_none()

        if subscription is None:
            return False

        now = datetime.now(timezone.utc)

        if subscription.status != "active" or subscription.ends_at > now:
            return False

        user_repository = UserRepository(session)
        course_repository = CourseRepository(session)

        user = await user_repository.get_by_id(subscription.user_id)

        course = await course_repository.get_by_id(subscription.course_id)

        if user is None or course is None:
            return False

        if course.requires_subscription and course.telegram_channel_id is not None:
            try:
                banned = await bot.ban_chat_member(
                    chat_id=(course.telegram_channel_id),
                    user_id=user.telegram_id,
                )

                if not banned:
                    raise RuntimeError("Telegram did not confirm ban")

                unbanned = await bot.unban_chat_member(
                    chat_id=(course.telegram_channel_id),
                    user_id=user.telegram_id,
                    only_if_banned=True,
                )

                if not unbanned:
                    raise RuntimeError("Telegram did not confirm unban")

            except Exception as error:
                logger.exception(
                    "Could not revoke channel "
                    "access "
                    "subscription_id=%s "
                    "telegram_user_id=%s "
                    "course_slug=%s",
                    subscription.id,
                    user.telegram_id,
                    course.slug,
                )

                raise ChannelAccessError(
                    "Не удалось отозвать доступ к каналу."
                ) from error

        subscription.status = "cancelled"

        await session.commit()

        logger.info(
            "Expired subscription revoked "
            "subscription_id=%s "
            "telegram_user_id=%s "
            "course_slug=%s",
            subscription.id,
            user.telegram_id,
            course.slug,
        )

        return True
