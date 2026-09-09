from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Subscription
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

@dataclass(frozen=True)
class SubscriptionView:
    course_slug: str
    course_title: str
    requires_subscription: bool

    status: str
    starts_at: datetime | None
    ends_at: datetime | None

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
):
    if days <= 0:
        raise ValueError(
            "Количество дней должно быть больше 0."
        )

    now = datetime.now(timezone.utc)

    repository = SubscriptionRepository(
        session
    )

    subscription = (
        await repository.get_by_user_and_course(
            user_id=user_id,
            course_id=course_id,
        )
    )

    if subscription is None:
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

    return subscription