from dataclasses import dataclass
from datetime import datetime, timezone

from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.hint_repository import HintRepository
from app.database.repositories.project_repository import ProjectRepository
from app.database.repositories.scheduled_post_repository import (
    ScheduledPostRepository,
)
from app.database.session import (
    async_session_factory,
)
from aiogram import Bot

from app.services.publishing_service import (
    publish_scheduled_post,
)


class ScheduleError(Exception):
    pass


class ScheduledPostNotFound(ScheduleError):
    pass


class ScheduledPostNotEditable(ScheduleError):
    pass


@dataclass(frozen=True)
class ScheduledPostItem:
    id: int
    post_type: str
    scheduled_at: datetime
    status: str
    project_id: int | None
    hint_id: int | None

@dataclass(frozen=True)
class ScheduledPostDetail:
    id: int
    course_slug: str
    post_type: str
    content: str
    scheduled_at: datetime
    status: str
    project_id: int | None
    hint_id: int | None
    error_message: str | None

@dataclass(frozen=True)
class ScheduleProjectItem:
    id: int
    number: int
    title: str

@dataclass(frozen=True)
class ScheduleHintItem:
    id: int
    number: int
    project_id: int


async def create_scheduled_post(
    *,
    course_slug: str,
    post_type: str,
    content: str,
    scheduled_at: datetime,
    project_id: int | None = None,
    hint_id: int | None = None,
) -> ScheduledPostItem:
    if scheduled_at <= datetime.now(timezone.utc):
        raise ScheduleError(
            "Время публикации должно быть в будущем."
        )

    if post_type not in {
        "regular",
        "project",
        "hint",
    }:
        raise ScheduleError(
            "Неизвестный тип публикации."
        )

    async with async_session_factory() as session:
        course_repository = CourseRepository(
            session
        )
        post_repository = ScheduledPostRepository(
            session
        )

        course = await course_repository.get_by_slug(
            course_slug
        )

        if course is None:
            raise ScheduleError(
                "Курс не найден."
            )

        post = await post_repository.create(
            course_id=course.id,
            post_type=post_type,
            content=content,
            scheduled_at=scheduled_at,
            project_id=project_id,
            hint_id=hint_id,
        )

        await session.commit()

        return ScheduledPostItem(
            id=post.id,
            post_type=post.post_type,
            scheduled_at=post.scheduled_at,
            status=post.status,
            project_id=post.project_id,
            hint_id=post.hint_id,
        )

async def reschedule_post(
    post_id: int,
    scheduled_at: datetime,
) -> None:
    if scheduled_at <= datetime.now(timezone.utc):
        raise ScheduleError(
            "Новое время должно быть в будущем."
        )

    async with async_session_factory() as session:
        repository = ScheduledPostRepository(
            session
        )

        post = await repository.get_by_id(
            post_id
        )

        if post is None:
            raise ScheduledPostNotFound()

        if post.status not in {
            "scheduled",
            "failed",
        }:
            raise ScheduledPostNotEditable(
                "Эту публикацию нельзя перенести."
            )

        await repository.reschedule(
            post,
            scheduled_at,
        )

        await session.commit()

async def cancel_scheduled_post(
    post_id: int,
) -> None:
    async with async_session_factory() as session:
        repository = ScheduledPostRepository(
            session
        )

        post = await repository.get_by_id(
            post_id
        )

        if post is None:
            raise ScheduledPostNotFound()

        if post.status != "scheduled":
            raise ScheduledPostNotEditable(
                "Можно отменить только "
                "запланированную публикацию."
            )

        await repository.cancel(post)

        await session.commit()

async def publish_post_now(
    post_id: int,
    bot: Bot,
) -> None:
    async with async_session_factory() as session:
        repository = ScheduledPostRepository(
            session
        )

        post = await repository.get_by_id(
            post_id
        )

        if post is None:
            raise ScheduledPostNotFound()

        if post.status not in {
            "scheduled",
            "failed",
        }:
            raise ScheduledPostNotEditable(
                "Эту публикацию нельзя "
                "опубликовать сейчас."
            )

        if post.status == "failed":
            await repository.reschedule(
                post,
                datetime.now(timezone.utc),
            )

            await session.commit()

    await publish_scheduled_post(
        post_id=post_id,
        bot=bot,
    )

async def get_course_schedule(
    course_slug: str,
) -> list[ScheduledPostItem]:
    async with async_session_factory() as session:
        course_repository = CourseRepository(
            session
        )
        post_repository = ScheduledPostRepository(
            session
        )

        course = await course_repository.get_by_slug(
            course_slug
        )

        if course is None:
            raise ScheduleError(
                "Курс не найден."
            )

        posts = (
            await post_repository
            .get_manageable_by_course(
                course.id
            )
        )

        return [
            ScheduledPostItem(
                id=post.id,
                post_type=post.post_type,
                scheduled_at=post.scheduled_at,
                status=post.status,
                project_id=post.project_id,
                hint_id=post.hint_id,
            )
            for post in posts
        ]

async def get_scheduled_post_detail(
    post_id: int,
) -> ScheduledPostDetail:
    async with async_session_factory() as session:
        post_repository = ScheduledPostRepository(
            session
        )
        course_repository = CourseRepository(
            session
        )

        post = await post_repository.get_by_id(
            post_id
        )

        if post is None:
            raise ScheduledPostNotFound()

        course = await course_repository.get_by_id(
            post.course_id
        )

        if course is None:
            raise ScheduleError(
                "Курс публикации не найден."
            )

        return ScheduledPostDetail(
            id=post.id,
            course_slug=course.slug,
            post_type=post.post_type,
            content=post.content,
            scheduled_at=post.scheduled_at,
            status=post.status,
            project_id=post.project_id,
            hint_id=post.hint_id,
            error_message=post.error_message,
        )

async def get_course_projects_for_schedule(
    course_slug: str,
) -> list[ScheduleProjectItem]:
    async with async_session_factory() as session:
        course_repository = CourseRepository(
            session
        )
        project_repository = ProjectRepository(
            session
        )

        course = await course_repository.get_by_slug(
            course_slug
        )

        if course is None:
            raise ScheduleError(
                "Курс не найден."
            )

        projects = await project_repository.get_by_course(
            course.id
        )

        return [
            ScheduleProjectItem(
                id=project.id,
                number=project.number,
                title=project.title,
            )
            for project in projects
        ]

async def get_project_hints_for_schedule(
    project_id: int,
) -> list[ScheduleHintItem]:
    async with async_session_factory() as session:
        hint_repository = HintRepository(
            session
        )

        hints = await hint_repository.get_by_project(
            project_id
        )

        return [
            ScheduleHintItem(
                id=hint.id,
                number=hint.number,
                project_id=hint.project_id,
            )
            for hint in hints
        ]