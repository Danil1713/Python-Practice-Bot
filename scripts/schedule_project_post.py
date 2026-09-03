import asyncio
from datetime import datetime, timedelta, timezone

from app.database.models.scheduled_post import ScheduledPost
from app.database.repositories.course_repository import CourseRepository
from app.database.repositories.project_repository import ProjectRepository
from app.database.session import async_session_factory, engine


PROJECT_NUMBER = 3


async def main() -> None:
    async with async_session_factory() as session:
        course_repository = CourseRepository(session)
        project_repository = ProjectRepository(session)

        demo = await course_repository.get_by_slug(
            "demo"
        )

        if demo is None:
            raise RuntimeError(
                "Demo course not found"
            )

        projects = await project_repository.get_by_course(
            demo.id
        )

        project = next(
            (
                item
                for item in projects
                if item.number == PROJECT_NUMBER
            ),
            None,
        )

        if project is None:
            raise RuntimeError(
                f"Project {PROJECT_NUMBER} not found"
            )

        post = ScheduledPost(
            course_id=demo.id,
            post_type="project",
            project_id=project.id,
            hint_id=None,
            content=(
                f"🚀 <b>Project {project.number}</b>\n\n"
                f"<b>{project.title}</b>\n\n"
                "Тест автоматической публикации проекта."
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
            f"Scheduled Project {project.number}, "
            f"post ID: {post.id}"
        )


async def run() -> None:
    try:
        await main()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())