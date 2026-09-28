from dataclasses import dataclass
from datetime import (
    datetime,
)

from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.user_repository import (
    UserRepository,
)
from app.database.session import (
    async_session_factory,
)
from app.services.subscription_service import (
    SubscriptionAuditContext,
    activate_or_extend_subscription_in_session,
)


class AdminSubscriptionError(Exception):
    pass


class UserNotFound(AdminSubscriptionError):
    pass


class CourseNotFound(AdminSubscriptionError):
    pass

MAX_ADMIN_SUBSCRIPTION_DAYS = 3650


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
    actor_telegram_id: int,
    idempotency_key: str,
) -> SubscriptionResult:
    if days <= 0:
        raise AdminSubscriptionError(
            "Количество дней должно быть больше 0."
        )

    if days > MAX_ADMIN_SUBSCRIPTION_DAYS:
        raise AdminSubscriptionError(
            "Нельзя выдать подписку "
            f"больше чем на "
            f"{MAX_ADMIN_SUBSCRIPTION_DAYS} дней."
        )

    async with async_session_factory() as session:
        user_repository = UserRepository(
            session
        )
        course_repository = CourseRepository(
            session
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

        if not course.requires_subscription:
            raise AdminSubscriptionError(
                "Для этого курса подписка "
                "не требуется."
            )

        subscription = (
            await activate_or_extend_subscription_in_session(
                session=session,
                user_id=user.id,
                course_id=course.id,
                days=days,
                audit=SubscriptionAuditContext(
                    actor_telegram_id=(
                        actor_telegram_id
                    ),
                    source="admin",
                    reason="manual_admin_grant",
                    idempotency_key=(
                        idempotency_key
                    ),
                ),
            )
        )

        await session.commit()

        return SubscriptionResult(
            user_id=user.id,
            course_id=course.id,
            starts_at=subscription.starts_at,
            ends_at=subscription.ends_at,
            status=subscription.status,
        )

async def activate_or_extend_subscription_by_slug(
    *,
    user_id: int,
    course_slug: str,
    days: int,
    actor_telegram_id: int,
    idempotency_key: str,
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
        actor_telegram_id=actor_telegram_id,
        idempotency_key=idempotency_key,
    )