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