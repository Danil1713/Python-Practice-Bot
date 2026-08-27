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
        user_repository = UserRepository(
            session
        )
        course_repository = CourseRepository(
            session
        )
        subscription_repository = (
            SubscriptionRepository(session)
        )

        user = await user_repository.get_by_telegram_id(
            telegram_user_id
        )

        if user is None:
            return False

        course = await course_repository.get_by_slug(
            course_slug
        )

        if course is None:
            return False

        subscription = (
            await subscription_repository
            .get_active_subscription(
                user_id=user.id,
                course_id=course.id,
            )
        )

        return subscription is not None