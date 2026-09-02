from dataclasses import dataclass

from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.project_repository import (
    ProjectRepository,
)
from app.database.repositories.user_project_repository import (
    UserProjectRepository,
)
from app.database.repositories.user_repository import (
    UserRepository,
)
from app.database.session import (
    async_session_factory,
)


@dataclass(frozen=True)
class ProgressProjectItem:
    number: int
    title: str
    status: str


@dataclass(frozen=True)
class CourseProgressView:
    course_slug: str
    course_title: str

    completed_count: int
    total_count: int
    percent: int

    projects: list[ProgressProjectItem]


async def get_course_progress(
    telegram_user_id: int,
    course_slug: str,
) -> CourseProgressView | None:
    async with async_session_factory() as session:
        user_repository = UserRepository(
            session
        )
        course_repository = CourseRepository(
            session
        )
        project_repository = ProjectRepository(
            session
        )
        user_project_repository = UserProjectRepository(
            session
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

        projects = await project_repository.get_by_course(
            course.id
        )

        project_ids = [
            project.id
            for project in projects
        ]

        completed_ids = (
            await user_project_repository
            .get_completed_project_ids(
                user_id=user.id,
                project_ids=project_ids,
            )
        )

        completed_count = len(completed_ids)
        total_count = len(projects)

        if total_count == 0:
            percent = 0
        else:
            percent = round(
                completed_count
                / total_count
                * 100
            )

        items: list[ProgressProjectItem] = []

        for project in projects:
            if project.id in completed_ids:
                status = "completed"

            elif project.published_at is None:
                status = "locked"

            else:
                status = "available"

            items.append(
                ProgressProjectItem(
                    number=project.number,
                    title=project.title,
                    status=status,
                )
            )

        return CourseProgressView(
            course_slug=course.slug,
            course_title=course.title,
            completed_count=completed_count,
            total_count=total_count,
            percent=percent,
            projects=items,
        )