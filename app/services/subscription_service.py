from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Subscription
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


@dataclass(frozen=True)
class SubscriptionView:
    course_slug: str
    course_title: str
    requires_subscription: bool

    status: str
    starts_at: datetime | None
    ends_at: datetime | None

@dataclass(frozen=True)
class SubscriptionAuditContext:
    actor_telegram_id: int
    source: str
    reason: str
    idempotency_key: str

async def has_active_subscription(
    telegram_user_id: int,
    course_slug: str,
) -> bool:
    async with async_session_factory() as session:
        course_repository = CourseRepository(session)

        course = await course_repository.get_by_slug(
            course_slug
        )

        if course is None:
            return False

        if not course.requires_subscription:
            return True

        user_repository = UserRepository(session)

        user = await user_repository.get_by_telegram_id(
            telegram_user_id
        )

        if user is None:
            return False

        subscription_repository = (
            SubscriptionRepository(session)
        )

        subscription = (
            await subscription_repository
            .get_active_subscription(
                user_id=user.id,
                course_id=course.id,
            )
        )

        return subscription is not None

async def get_subscription_view(
    telegram_user_id: int,
    course_slug: str,
) -> SubscriptionView | None:
    async with async_session_factory() as session:
        user_repository = UserRepository(session)
        course_repository = CourseRepository(session)
        subscription_repository = (
            SubscriptionRepository(session)
        )

        user = await user_repository.get_by_telegram_id(
            telegram_user_id
        )

        if user is None:
            return None

        course = await course_repository.get_by_slug(
            course_slug
        )

        if course is None:
            return None

        if not course.requires_subscription:
            return SubscriptionView(
                course_slug=course.slug,
                course_title=course.title,
                requires_subscription=False,
                status="free",
                starts_at=None,
                ends_at=None,
            )

        subscription = (
            await subscription_repository
            .get_by_user_and_course(
                user_id=user.id,
                course_id=course.id,
            )
        )

        if subscription is None:
            return SubscriptionView(
                course_slug=course.slug,
                course_title=course.title,
                requires_subscription=True,
                status="inactive",
                starts_at=None,
                ends_at=None,
            )

        now = datetime.now(timezone.utc)

        if (
            subscription.status == "active"
            and subscription.starts_at <= now
            and subscription.ends_at > now
        ):
            status = "active"
        else:
            status = "expired"

        return SubscriptionView(
            course_slug=course.slug,
            course_title=course.title,
            requires_subscription=True,
            status=status,
            starts_at=subscription.starts_at,
            ends_at=subscription.ends_at,
        )


async def activate_or_extend_subscription_in_session(
    *,
    session: AsyncSession,
    user_id: int,
    course_id: int,
    days: int,
    audit: SubscriptionAuditContext | None = None,
):
    if days <= 0:
        raise ValueError(
            "Количество дней должно быть больше 0."
        )

    now = datetime.now(
        timezone.utc
    )

    repository = SubscriptionRepository(
        session
    )

    event_repository = (
        SubscriptionEventRepository(
            session
        )
    )

    await repository.lock_subscription(
        user_id=user_id,
        course_id=course_id,
    )

    if audit is not None:
        existing_event = (
            await event_repository
            .get_by_idempotency_key(
                audit.idempotency_key
            )
        )

        if existing_event is not None:
            if (
                existing_event.user_id
                != user_id
                or existing_event.course_id
                != course_id
            ):
                raise RuntimeError(
                    "Idempotency key используется "
                    "для другой подписки."
                )

            subscription = (
                await repository
                .get_by_user_and_course(
                    user_id=user_id,
                    course_id=course_id,
                )
            )

            if subscription is None:
                raise RuntimeError(
                    "Audit event существует, "
                    "но подписка не найдена."
                )

            return subscription

    subscription = (
        await repository
        .get_by_user_and_course(
            user_id=user_id,
            course_id=course_id,
        )
    )

    if subscription is None:
        old_status = None
        old_starts_at = None
        old_ends_at = None

        subscription = Subscription(
            user_id=user_id,
            course_id=course_id,
            status="active",
            starts_at=now,
            ends_at=(
                now
                + timedelta(days=days)
            ),
        )

        await repository.save(
            subscription
        )

    else:
        old_status = subscription.status
        old_starts_at = (
            subscription.starts_at
        )
        old_ends_at = (
            subscription.ends_at
        )

        if (
            subscription.status == "active"
            and subscription.ends_at > now
        ):
            subscription.ends_at = (
                subscription.ends_at
                + timedelta(days=days)
            )

        else:
            subscription.starts_at = now
            subscription.ends_at = (
                now
                + timedelta(days=days)
            )

        subscription.status = "active"

    await session.flush()

    if audit is not None:
        await event_repository.create(
            subscription_id=subscription.id,
            user_id=user_id,
            course_id=course_id,
            actor_telegram_id=(
                audit.actor_telegram_id
            ),
            event_type="activate_or_extend",
            source=audit.source,
            reason=audit.reason,
            days=days,
            old_status=old_status,
            new_status=subscription.status,
            old_starts_at=old_starts_at,
            new_starts_at=(
                subscription.starts_at
            ),
            old_ends_at=old_ends_at,
            new_ends_at=(
                subscription.ends_at
            ),
            idempotency_key=(
                audit.idempotency_key
            ),
        )

    return subscription