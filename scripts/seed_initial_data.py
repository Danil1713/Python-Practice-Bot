import asyncio
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert

from app.database.models.hint import Hint
from app.database.models.project import Project
from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.project_repository import (
    ProjectRepository,
)
from app.database.session import (
    async_session_factory,
    engine,
)


async def seed() -> None:
    async with async_session_factory() as session:
        course_repository = CourseRepository(session)

        demo = await course_repository.get_by_slug(
            "demo"
        )

        if demo is None:
            raise RuntimeError(
                "Demo course не найден. "
                "Сначала выполни alembic upgrade head."
            )

        now = datetime.now(timezone.utc)

        projects = [
            {
                "course_id": demo.id,
                "number": 1,
                "title": "Mini Casino 🎰",
                "max_xp": 100,
                "published_at": now,
            },
            {
                "course_id": demo.id,
                "number": 2,
                "title": "Smart File Sorter 📁",
                "max_xp": 100,
                "published_at": now,
            },
            {
                "course_id": demo.id,
                "number": 3,
                "title": "Backend Web App 🌐",
                "max_xp": 100,
                "published_at": None,
            },
        ]

        for project in projects:
            statement = (
                insert(Project)
                .values(**project)
                .on_conflict_do_nothing(
                    index_elements=[
                        Project.course_id,
                        Project.number,
                    ]
                )
            )

            await session.execute(statement)

        await session.commit()

        project_repository = ProjectRepository(
            session
        )

        demo_projects = (
            await project_repository.get_by_course(
                demo.id
            )
        )

        projects_by_number = {
            project.number: project
            for project in demo_projects
        }

        hints = [
            # Mini Casino
            {
                "project_id": projects_by_number[1].id,
                "number": 1,
                "xp_after_publish": 80,
                "published_at": now,
            },
            {
                "project_id": projects_by_number[1].id,
                "number": 2,
                "xp_after_publish": 60,
                "published_at": now,
            },
            {
                "project_id": projects_by_number[1].id,
                "number": 3,
                "xp_after_publish": 40,
                "published_at": now,
            },

            # Smart File Sorter
            {
                "project_id": projects_by_number[2].id,
                "number": 1,
                "xp_after_publish": 80,
                "published_at": now,
            },
            {
                "project_id": projects_by_number[2].id,
                "number": 2,
                "xp_after_publish": 60,
                "published_at": now,
            },
            {
                "project_id": projects_by_number[2].id,
                "number": 3,
                "xp_after_publish": 40,
                "published_at": now,
            },
        ]

        for hint in hints:
            statement = (
                insert(Hint)
                .values(**hint)
                .on_conflict_do_nothing(
                    index_elements=[
                        Hint.project_id,
                        Hint.number,
                    ]
                )
            )

            await session.execute(statement)

        await session.commit()


async def main() -> None:
    try:
        await seed()

        print(
            "Initial Demo data created."
        )

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())