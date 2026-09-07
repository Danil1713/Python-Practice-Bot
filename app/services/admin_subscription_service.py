from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)

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


class AdminSubscriptionError(Exception):
    pass


class UserNotFound(AdminSubscriptionError):
    pass


class CourseNotFound(AdminSubscriptionError):
    pass


@dataclass(frozen=True)
class AdminUserItem:
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None


@dataclass(frozen=True)
class SubscriptionResult:
    user_id: int
    course_id: int
    starts_at: datetime
    ends_at: datetime
    status: str


async def search_users(
        value: str,
) -> list[AdminUserItem]:
    async with async_session_factory() as session:
        repository = UserRepository(
            session
        )

        users = await repository.search(
            value
        )

        return [
            AdminUserItem(
                id=user.id,
                telegram_id=user.telegram_id,
                username=user.username,
                first_name=user.first_name,
            )
            for user in users
        ]

async def activate_or_extend_subscription(
    *,
    user_id: int,
    course_id: int,
    days: int,
) -> SubscriptionResult:
    if days <= 0:
        raise AdminSubscriptionError(
            "Количество дней должно быть больше 0."
        )

    now = datetime.now(
        timezone.utc
    )

    async with async_session_factory() as session:
        user_repository = UserRepository(
            session
        )
        course_repository = CourseRepository(
            session
        )
        subscription_repository = (
            SubscriptionRepository(session)
        )

        user = await user_repository.get_by_id(
            user_id
        )

        if user is None:
            raise UserNotFound(
                "Пользователь не найден."
            )

        course = await course_repository.get_by_id(
            course_id
        )

        if course is None:
            raise CourseNotFound(
                "Курс не найден."
            )

        subscription = (
            await subscription_repository
            .get_by_user_and_course(
                user_id=user.id,
                course_id=course.id,
            )
        )

        if subscription is None:
            starts_at = now
            ends_at = (
                now
                + timedelta(days=days)
            )

            subscription = Subscription(
                user_id=user.id,
                course_id=course.id,
                status="active",
                starts_at=starts_at,
                ends_at=ends_at,
            )

            await subscription_repository.save(
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

        await session.commit()

        return SubscriptionResult(
            user_id=user.id,
            course_id=course.id,
            starts_at=subscription.starts_at,
            ends_at=subscription.ends_at,
            status=subscription.status,
        )


async def deactivate_subscription(
    *,
    user_id: int,
    course_id: int,
) -> None:
    async with async_session_factory() as session:
        repository = SubscriptionRepository(
            session
        )

        subscription = (
            await repository
            .get_by_user_and_course(
                user_id=user_id,
                course_id=course_id,
            )
        )

        if subscription is None:
            raise AdminSubscriptionError(
                "Подписка не найдена."
            )

        subscription.status = "cancelled"

        await session.commit()

async def activate_or_extend_subscription_by_slug(
    *,
    user_id: int,
    course_slug: str,
    days: int,
) -> SubscriptionResult:
    async with async_session_factory() as session:
        course_repository = CourseRepository(
            session
        )

        course = await course_repository.get_by_slug(
            course_slug
        )

        if course is None:
            raise CourseNotFound(
                "Курс не найден."
            )

        course_id = course.id

    return await activate_or_extend_subscription(
        user_id=user_id,
        course_id=course_id,
        days=days,
    )