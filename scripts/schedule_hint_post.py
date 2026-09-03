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
from app.database.repositories.hint_repository import (
    HintRepository,
)
from app.database.repositories.project_repository import (
    ProjectRepository,
)
from app.database.session import (
    async_session_factory,
    engine,
)


PROJECT_NUMBER = 3
HINT_NUMBER = 2


async def main() -> None:
    async with async_session_factory() as session:
        course_repository = CourseRepository(session)
        project_repository = ProjectRepository(session)
        hint_repository = HintRepository(session)

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

        hints = await hint_repository.get_by_project(
            project.id
        )

        hint = next(
            (
                item
                for item in hints
                if item.number == HINT_NUMBER
            ),
            None,
        )

        if hint is None:
            raise RuntimeError(
                f"Hint {HINT_NUMBER} not found"
            )

        post = ScheduledPost(
            course_id=demo.id,
            post_type="hint",
            project_id=project.id,
            hint_id=hint.id,
            content=(
                f"💡 <b>Подсказка {hint.number}</b>\n\n"
                f"Project {project.number} — "
                f"{project.title}\n\n"
                "Тест автоматической публикации "
                "подсказки."
            ),
            scheduled_at=(
                datetime.now(timezone.utc)
                + timedelta(seconds=30)
            ),
            status="scheduled",
        )

        session.add(post)

        await session.commit()

        print(
            f"Scheduled Hint {hint.number} "
            f"for Project {project.number}."
        )


async def run() -> None:
    try:
        await main()

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())