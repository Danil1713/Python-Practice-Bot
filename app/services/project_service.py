from dataclasses import dataclass
from typing import Literal

from sqlalchemy.exc import IntegrityError

from app.database.repositories.attempt_repository import (
    AttemptRepository,
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
from app.database.repositories.user_project_repository import (
    UserProjectRepository,
)
from app.database.repositories.user_repository import (
    UserRepository,
)
from app.database.session import (
    async_session_factory,
)

ProjectStatus = Literal[
    "locked",
    "available",
    "pending",
    "completed",
]


class ProjectCreationError(Exception):
    pass


@dataclass(frozen=True)
class CreatedProject:
    id: int
    number: int
    title: str


@dataclass(frozen=True)
class ProjectListItem:
    id: int
    number: int
    title: str
    status: ProjectStatus


@dataclass(frozen=True)
class CourseProjectsView:
    course_slug: str
    course_title: str
    projects: list[ProjectListItem]


@dataclass(frozen=True)
class ProjectCard:
    id: int
    course_slug: str
    course_title: str
    number: int
    title: str
    status: ProjectStatus
    max_xp: int
    current_xp: int
    awarded_xp: int | None
    telegram_message_id: int | None
    telegram_channel_id: int | None


async def get_course_projects(
    telegram_user_id: int,
    course_slug: str,
) -> CourseProjectsView | None:
    async with async_session_factory() as session:
        course_repository = CourseRepository(session)
        user_repository = UserRepository(session)
        project_repository = ProjectRepository(session)
        user_project_repository = UserProjectRepository(session)
        attempt_repository = AttemptRepository(session)

        course = await course_repository.get_by_slug(course_slug)

        if course is None:
            return None

        projects = await project_repository.get_by_course(course.id)

        user = await user_repository.get_by_telegram_id(telegram_user_id)

        completed_ids: set[int] = set()

        if user is not None:
            completed_ids = await user_project_repository.get_completed_project_ids(
                user_id=user.id,
                project_ids=[project.id for project in projects],
            )

        pending_ids: set[int] = set()

        if user is not None:
            pending_ids = await attempt_repository.get_pending_project_ids(
                user_id=user.id,
                project_ids=[project.id for project in projects],
            )

        items: list[ProjectListItem] = []

        for project in projects:
            if project.id in completed_ids:
                status: ProjectStatus = "completed"

            elif project.id in pending_ids:
                status = "pending"

            elif project.published_at is None:
                status = "locked"

            else:
                status = "available"

            items.append(
                ProjectListItem(
                    id=project.id,
                    number=project.number,
                    title=project.title,
                    status=status,
                )
            )

        return CourseProjectsView(
            course_slug=course.slug,
            course_title=course.title,
            projects=items,
        )


async def get_project_card(
    telegram_user_id: int,
    project_id: int,
) -> ProjectCard | None:
    async with async_session_factory() as session:
        project_repository = ProjectRepository(session)
        course_repository = CourseRepository(session)
        user_repository = UserRepository(session)
        user_project_repository = UserProjectRepository(session)
        hint_repository = HintRepository(session)
        attempt_repository = AttemptRepository(session)

        project = await project_repository.get_by_id(project_id)

        if project is None:
            return None

        course = await course_repository.get_by_id(project.course_id)

        if course is None:
            return None

        user = await user_repository.get_by_telegram_id(telegram_user_id)

        completed = None

        if user is not None:
            completed = await user_project_repository.get_completed_project(
                user_id=user.id,
                project_id=project.id,
            )

        pending_attempt = None

        if user is not None:
            pending_attempt = await attempt_repository.get_active_for_project(
                user_id=user.id,
                project_id=project.id,
            )

        if completed is not None:
            status: ProjectStatus = "completed"

        elif pending_attempt is not None:
            status = "pending"

        elif project.published_at is None:
            status = "locked"

        else:
            status = "available"

        latest_hint = await hint_repository.get_latest_published(project.id)

        if latest_hint is not None:
            current_xp = latest_hint.xp_after_publish
        else:
            current_xp = project.max_xp

        return ProjectCard(
            id=project.id,
            course_slug=course.slug,
            course_title=course.title,
            number=project.number,
            title=project.title,
            status=status,
            max_xp=project.max_xp,
            current_xp=current_xp,
            awarded_xp=(completed.awarded_xp if completed is not None else None),
            telegram_message_id=(project.telegram_message_id),
            telegram_channel_id=(course.telegram_channel_id),
        )


async def create_project(
    course_slug: str,
    title: str,
    ai_requirements: str,
) -> CreatedProject:
    title = title.strip()
    ai_requirements = ai_requirements.strip()

    if not title:
        raise ProjectCreationError("Название проекта не может быть пустым.")

    if len(title) > 255:
        raise ProjectCreationError("Название проекта не должно превышать 255 символов.")

    if not ai_requirements:
        raise ProjectCreationError("Обязательные критерии не могут быть пустыми.")

    async with async_session_factory() as session:
        course_repository = CourseRepository(session)
        project_repository = ProjectRepository(session)

        course = await course_repository.get_by_slug(course_slug)

        if course is None:
            raise ProjectCreationError("Курс не найден или недоступен.")

        await project_repository.lock_creation(course.id)

        number = await project_repository.get_next_number(course.id)

        try:
            project = await project_repository.create(
                course_id=course.id,
                number=number,
                title=title,
                ai_requirements=ai_requirements,
            )

            await session.commit()

        except IntegrityError as error:
            await session.rollback()

            raise ProjectCreationError(
                "Не удалось создать проект из-за конфликта данных."
            ) from error

        return CreatedProject(
            id=project.id,
            number=project.number,
            title=project.title,
        )
