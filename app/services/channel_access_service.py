import logging
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from html import escape
from typing import Literal

from aiogram import Bot

from app.bot.keyboards.notifications import get_dismiss_notification_keyboard
from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.subscription_event_repository import (
    SubscriptionEventRepository,
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

REVOCATION_STUCK_AFTER_MINUTES = 15


class ChannelAccessError(Exception):
    pass


@dataclass(frozen=True)
class ChannelRevocationTarget:
    subscription_id: int
    telegram_user_id: int
    course_slug: str
    course_title: str
    requires_subscription: bool
    telegram_channel_id: int | None


RevocationFinalizeResult = Literal[
    "cancelled",
    "renewed",
    "skipped",
]


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

    stale_before = now - timedelta(minutes=REVOCATION_STUCK_AFTER_MINUTES)

    async with async_session_factory() as session:
        repository = SubscriptionRepository(session)

        return await repository.get_revocation_candidate_ids(
            now=now,
            stale_before=stale_before,
            limit=limit,
        )


async def _claim_expired_subscription(
    subscription_id: int,
) -> ChannelRevocationTarget | None:
    now = datetime.now(timezone.utc)

    stale_before = now - timedelta(minutes=REVOCATION_STUCK_AFTER_MINUTES)

    async with async_session_factory() as session:
        subscription_repository = SubscriptionRepository(session)

        subscription = await subscription_repository.get_by_id_for_update(
            subscription_id
        )

        if subscription is None:
            return None

        expired_active = subscription.status == "active" and subscription.ends_at <= now

        stale_revoking = (
            subscription.status == "revoking"
            and subscription.updated_at <= stale_before
        )

        if not (expired_active or stale_revoking):
            return None

        user_repository = UserRepository(session)
        course_repository = CourseRepository(session)

        user = await user_repository.get_by_id(subscription.user_id)

        course = await course_repository.get_by_id(subscription.course_id)

        if user is None or course is None:
            return None

        await subscription_repository.mark_revoking(
            subscription,
            started_at=now,
        )

        await session.commit()

        return ChannelRevocationTarget(
            subscription_id=subscription.id,
            telegram_user_id=user.telegram_id,
            course_slug=course.slug,
            course_title=course.title,
            requires_subscription=course.requires_subscription,
            telegram_channel_id=course.telegram_channel_id,
        )


async def _restore_revocation_claim(
    subscription_id: int,
) -> None:
    async with async_session_factory() as session:
        repository = SubscriptionRepository(session)

        subscription = await repository.get_by_id_for_update(subscription_id)

        if subscription is None or subscription.status != "revoking":
            return

        await repository.restore_active(subscription)

        await session.commit()


async def _finalize_revocation_claim(
    subscription_id: int,
) -> RevocationFinalizeResult:
    now = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        repository = SubscriptionRepository(session)

        subscription = await repository.get_by_id_for_update(subscription_id)

        if subscription is None:
            return "skipped"

        if subscription.ends_at > now:
            if subscription.status == "revoking":
                await repository.restore_active(subscription)

                await session.commit()

            return "renewed"

        if subscription.status != "revoking":
            return "skipped"

        old_status = subscription.status

        await repository.mark_cancelled(subscription)

        event_repository = SubscriptionEventRepository(session)

        idempotency_key = f"expire:{subscription.id}:{subscription.ends_at.isoformat()}"

        existing_event = await event_repository.get_by_idempotency_key(idempotency_key)

        if existing_event is None:
            await event_repository.create(
                subscription_id=subscription.id,
                user_id=subscription.user_id,
                course_id=subscription.course_id,
                actor_telegram_id=None,
                event_type="subscription_expired",
                source="scheduler",
                reason="subscription_expired",
                days=None,
                old_status=old_status,
                new_status=subscription.status,
                old_starts_at=subscription.starts_at,
                new_starts_at=subscription.starts_at,
                old_ends_at=subscription.ends_at,
                new_ends_at=subscription.ends_at,
                idempotency_key=idempotency_key,
            )

        await session.commit()

        return "cancelled"


async def _restore_channel_for_renewed_user(
    *,
    target: ChannelRevocationTarget,
    bot: Bot,
) -> None:
    try:
        invite_link = await create_course_join_request_link(
            bot=bot,
            telegram_user_id=(target.telegram_user_id),
            course_slug=target.course_slug,
        )

        await bot.send_message(
            chat_id=target.telegram_user_id,
            text=(
                "✅ Подписка была продлена "
                "во время обновления доступа "
                "к каналу.\n\n"
                "Отправь новую заявку "
                "по ссылке:\n"
                f"{invite_link}"
            ),
        )

    except Exception:
        logger.exception(
            "Could not restore channel access "
            "after concurrent renewal "
            "subscription_id=%s "
            "telegram_user_id=%s "
            "course_slug=%s",
            target.subscription_id,
            target.telegram_user_id,
            target.course_slug,
        )


async def revoke_expired_subscription_access(
    *,
    subscription_id: int,
    bot: Bot,
) -> bool:
    target = await _claim_expired_subscription(subscription_id)

    if target is None:
        return False

    if target.requires_subscription and target.telegram_channel_id is not None:
        try:
            banned = await bot.ban_chat_member(
                chat_id=(target.telegram_channel_id),
                user_id=(target.telegram_user_id),
            )

            if not banned:
                raise RuntimeError("Telegram did not confirm ban")

            unbanned = await bot.unban_chat_member(
                chat_id=(target.telegram_channel_id),
                user_id=(target.telegram_user_id),
                only_if_banned=True,
            )

            if not unbanned:
                raise RuntimeError("Telegram did not confirm unban")

        except Exception as error:
            logger.exception(
                "Could not revoke channel access "
                "subscription_id=%s "
                "telegram_user_id=%s "
                "course_slug=%s",
                target.subscription_id,
                target.telegram_user_id,
                target.course_slug,
            )

            try:
                await _restore_revocation_claim(target.subscription_id)

            except Exception:
                logger.exception(
                    "Could not restore revocation claim subscription_id=%s",
                    target.subscription_id,
                )

            raise ChannelAccessError("Не удалось отозвать доступ к каналу.") from error

    result = await _finalize_revocation_claim(target.subscription_id)

    if result == "renewed":
        logger.warning(
            "Subscription was renewed during "
            "channel revocation "
            "subscription_id=%s "
            "telegram_user_id=%s "
            "course_slug=%s",
            target.subscription_id,
            target.telegram_user_id,
            target.course_slug,
        )

        await _restore_channel_for_renewed_user(
            target=target,
            bot=bot,
        )

        return False

    if result != "cancelled":
        return False

    logger.info(
        "Expired subscription revoked "
        "subscription_id=%s "
        "telegram_user_id=%s "
        "course_slug=%s",
        target.subscription_id,
        target.telegram_user_id,
        target.course_slug,
    )

    try:
        await bot.send_message(
            chat_id=target.telegram_user_id,
            text=(
                "⌛ <b>Подписка закончилась.</b>\n\n"
                f"Курс: <b>"
                f"{escape(target.course_title)}"
                f"</b>\n\n"
                "Доступ к Telegram-каналу закрыт.\n\n"
                "Чтобы продолжить обучение, "
                "открой раздел подписки "
                "и оформи доступ снова."
            ),
            reply_markup=get_dismiss_notification_keyboard(),
        )

    except Exception:
        logger.exception(
            "Could not notify user about expired subscription "
            "subscription_id=%s "
            "telegram_user_id=%s "
            "course_slug=%s",
            target.subscription_id,
            target.telegram_user_id,
            target.course_slug,
        )

    return True
