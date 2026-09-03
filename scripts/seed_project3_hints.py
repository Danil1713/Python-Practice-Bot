import asyncio

from sqlalchemy.dialects.postgresql import insert

from app.database.models.hint import Hint
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


HINTS = [
    (1, 80),
    (2, 60),
    (3, 40),
]


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
                if item.number == 3
            ),
            None,
        )

        if project is None:
            raise RuntimeError(
                "Project 3 not found"
            )

        for number, xp_after_publish in HINTS:
            statement = (
                insert(Hint)
                .values(
                    project_id=project.id,
                    number=number,
                    xp_after_publish=xp_after_publish,
                )
                .on_conflict_do_update(
                    index_elements=[
                        Hint.project_id,
                        Hint.number,
                    ],
                    set_={
                        "xp_after_publish": (
                            xp_after_publish
                        ),
                    },
                )
            )

            await session.execute(statement)

        await session.commit()

        print(
            "Project 3 hints created."
        )


async def run() -> None:
    try:
        await main()

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())