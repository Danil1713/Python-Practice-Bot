from dataclasses import dataclass
from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy.exc import IntegrityError

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
from app.services.publishing_service import (
    publish_scheduled_post,
)
from app.services.telegram_post_validation_service import (
    TelegramPostValidationError,
    validate_telegram_post_content,
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
    try:
        validate_telegram_post_content(content)

    except TelegramPostValidationError as error:
        raise ScheduleError(str(error)) from error

    if scheduled_at <= datetime.now(timezone.utc):
        raise ScheduleError("Время публикации должно быть в будущем.")

    if post_type not in {
        "regular",
        "project",
        "hint",
    }:
        raise ScheduleError("Неизвестный тип публикации.")

    async with async_session_factory() as session:
        course_repository = CourseRepository(session)
        post_repository = ScheduledPostRepository(session)

        course = await course_repository.get_by_slug(course_slug)

        project_repository = ProjectRepository(session)
        hint_repository = HintRepository(session)

        if course is None:
            raise ScheduleError("Курс не найден.")

        if post_type == "regular":
            if project_id is not None or hint_id is not None:
                raise ScheduleError(
                    "Обычная публикация не должна быть связана с Project или Hint."
                )

        elif post_type == "project":
            if project_id is None:
                raise ScheduleError("Для публикации Project нужно выбрать проект.")

            if hint_id is not None:
                raise ScheduleError("Публикация Project не может быть связана с Hint.")

            project = await project_repository.get_by_id(project_id)

            if project is None:
                raise ScheduleError("Project не найден.")

            if project.course_id != course.id:
                raise ScheduleError("Project принадлежит другому курсу.")

            if project.published_at is not None:
                raise ScheduleError("Этот Project уже опубликован.")

            duplicate = await post_repository.has_active_for_project(project.id)

            if duplicate:
                raise ScheduleError("Для этого Project уже есть активная публикация.")

        elif post_type == "hint":
            if hint_id is None:
                raise ScheduleError("Для публикации Hint нужно выбрать подсказку.")

            if project_id is not None:
                raise ScheduleError("Публикация Hint не должна содержать project_id.")

            hint = await hint_repository.get_by_id(hint_id)

            if hint is None:
                raise ScheduleError("Hint не найден.")

            project = await project_repository.get_by_id(hint.project_id)

            if project is None:
                raise ScheduleError("Project подсказки не найден.")

            if project.course_id != course.id:
                raise ScheduleError("Hint принадлежит другому курсу.")

            if project.published_at is None:
                raise ScheduleError("Сначала опубликуй Project.")

            if hint.number not in {
                1,
                2,
                3,
            }:
                raise ScheduleError("Некорректный номер Hint.")

            if hint.number > 1:
                hints = await hint_repository.get_by_project(project.id)

                published_numbers = {
                    item.number for item in hints if item.published_at is not None
                }

                required_numbers = set(
                    range(
                        1,
                        hint.number,
                    )
                )

                missing_numbers = required_numbers - published_numbers

                if missing_numbers:
                    missing_number = min(missing_numbers)

                    raise ScheduleError(f"Сначала опубликуй Hint {missing_number}.")

            if hint.published_at is not None:
                raise ScheduleError("Этот Hint уже опубликован.")

            duplicate = await post_repository.has_active_for_hint(hint.id)

            if duplicate:
                raise ScheduleError("Для этого Hint уже есть активная публикация.")

        try:
            post = await post_repository.create(
                course_id=course.id,
                post_type=post_type,
                content=content,
                scheduled_at=scheduled_at,
                project_id=project_id,
                hint_id=hint_id,
            )

            await session.commit()

        except IntegrityError as error:
            await session.rollback()

            if post_type == "project":
                raise ScheduleError(
                    "Для этого Project уже есть активная публикация."
                ) from error

            if post_type == "hint":
                raise ScheduleError(
                    "Для этого Hint уже есть активная публикация."
                ) from error

            raise ScheduleError("Не удалось создать публикацию.") from error

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
        raise ScheduleError("Новое время должно быть в будущем.")

    async with async_session_factory() as session:
        repository = ScheduledPostRepository(session)

        post = await repository.get_by_id(post_id)

        if post is None:
            raise ScheduledPostNotFound()

        try:
            validate_telegram_post_content(post.content)

        except TelegramPostValidationError as error:
            raise ScheduleError(str(error)) from error

        if post.status not in {
            "scheduled",
            "failed",
        }:
            raise ScheduledPostNotEditable("Эту публикацию нельзя перенести.")

        await ensure_no_active_duplicate(
            repository,
            post,
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
        repository = ScheduledPostRepository(session)

        post = await repository.get_by_id(post_id)

        if post is None:
            raise ScheduledPostNotFound()

        if post.status != "scheduled":
            raise ScheduledPostNotEditable(
                "Можно отменить только запланированную публикацию."
            )

        await repository.cancel(post)

        await session.commit()


async def publish_post_now(
    post_id: int,
    bot: Bot,
) -> None:
    async with async_session_factory() as session:
        repository = ScheduledPostRepository(session)

        post = await repository.get_by_id(post_id)

        if post is None:
            raise ScheduledPostNotFound()

        if post.status not in {
            "scheduled",
            "failed",
        }:
            raise ScheduledPostNotEditable("Эту публикацию нельзя опубликовать сейчас.")

        await ensure_no_active_duplicate(
            repository,
            post,
        )

        if post.status == "failed":
            await repository.reschedule(
                post,
                datetime.now(timezone.utc),
            )

            await session.commit()

    published = await publish_scheduled_post(
        post_id=post_id,
        bot=bot,
    )

    if not published:
        raise ScheduleError(
            "Публикация не была отправлена. Проверь статус и текст ошибки."
        )


async def get_course_schedule(
    course_slug: str,
) -> list[ScheduledPostItem]:
    async with async_session_factory() as session:
        course_repository = CourseRepository(session)
        post_repository = ScheduledPostRepository(session)

        course = await course_repository.get_by_slug(course_slug)

        if course is None:
            raise ScheduleError("Курс не найден.")

        posts = await post_repository.get_manageable_by_course(course.id)

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
        post_repository = ScheduledPostRepository(session)
        course_repository = CourseRepository(session)

        post = await post_repository.get_by_id(post_id)

        if post is None:
            raise ScheduledPostNotFound()

        course = await course_repository.get_by_id(post.course_id)

        if course is None:
            raise ScheduleError("Курс публикации не найден.")

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
        course_repository = CourseRepository(session)
        project_repository = ProjectRepository(session)
        post_repository = ScheduledPostRepository(session)

        course = await course_repository.get_by_slug(course_slug)

        if course is None:
            raise ScheduleError("Курс не найден.")

        projects = await project_repository.get_unpublished_by_course(course.id)

        result = []

        for project in projects:
            has_active_post = await post_repository.has_active_for_project(project.id)

            if has_active_post:
                continue

            result.append(
                ScheduleProjectItem(
                    id=project.id,
                    number=project.number,
                    title=project.title,
                )
            )

        return result


async def get_course_projects_for_hint_schedule(
    course_slug: str,
) -> list[ScheduleProjectItem]:
    async with async_session_factory() as session:
        course_repository = CourseRepository(session)
        project_repository = ProjectRepository(session)
        hint_repository = HintRepository(session)
        post_repository = ScheduledPostRepository(session)

        course = await course_repository.get_by_slug(course_slug)

        if course is None:
            raise ScheduleError("Курс не найден.")

        projects = await project_repository.get_available_for_hint_by_course(course.id)

        result = []

        for project in projects:
            hints = await hint_repository.get_unpublished_by_project(project.id)

            if not hints:
                result.append(
                    ScheduleProjectItem(
                        id=project.id,
                        number=project.number,
                        title=project.title,
                    )
                )
                continue

            has_available_hint = False

            for hint in hints:
                has_active_post = await post_repository.has_active_for_hint(hint.id)

                if not has_active_post:
                    has_available_hint = True
                    break

            if not has_available_hint:
                continue

            result.append(
                ScheduleProjectItem(
                    id=project.id,
                    number=project.number,
                    title=project.title,
                )
            )

        return result


async def get_project_hints_for_schedule(
    project_id: int,
) -> list[ScheduleHintItem]:
    async with async_session_factory() as session:
        hint_repository = HintRepository(session)
        post_repository = ScheduledPostRepository(session)

        hints = await hint_repository.get_unpublished_by_project(project_id)

        result = []

        for hint in hints:
            has_active_post = await post_repository.has_active_for_hint(hint.id)

            if has_active_post:
                continue

            result.append(
                ScheduleHintItem(
                    id=hint.id,
                    number=hint.number,
                    project_id=hint.project_id,
                )
            )

        return result


async def ensure_no_active_duplicate(
    repository: ScheduledPostRepository,
    post,
) -> None:
    if post.post_type == "project" and post.project_id is not None:
        duplicate = await repository.has_active_for_project(
            project_id=post.project_id,
            exclude_post_id=post.id,
        )

        if duplicate:
            raise ScheduleError(
                "Для этого Project уже есть другая активная публикация."
            )

    elif post.post_type == "hint" and post.hint_id is not None:
        duplicate = await repository.has_active_for_hint(
            hint_id=post.hint_id,
            exclude_post_id=post.id,
        )

        if duplicate:
            raise ScheduleError("Для этого Hint уже есть другая активная публикация.")
