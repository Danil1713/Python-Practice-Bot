import asyncio
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from app.database.models.scheduled_post import (
    ScheduledPost,
)
from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.session import (
    async_session_factory,
    engine,
)


async def main() -> None:
    async with async_session_factory() as session:
        course_repository = CourseRepository(
            session
        )

        demo = await course_repository.get_by_slug(
            "demo"
        )

        if demo is None:
            raise RuntimeError(
                "Demo course not found"
            )

        post = ScheduledPost(
            course_id=demo.id,
            post_type="regular",
            project_id=None,
            hint_id=None,
            content=(
                "🧪 Тест автоматической публикации.\n\n"
                "Если ты видишь этот пост — "
                "scheduler работает."
            ),
            scheduled_at=(
                datetime.now(timezone.utc)
                + timedelta(minutes=2)
            ),
            status="scheduled",
        )

        session.add(post)

        await session.commit()

        print(
            f"Scheduled post ID: {post.id}"
        )


async def run() -> None:
    try:
        await main()

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())