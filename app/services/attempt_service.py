from dataclasses import dataclass
from datetime import datetime

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
from app.exceptions.attempts import (
    AttemptAILimitReached,
    AttemptAlreadyPending,
    AttemptError,
    AttemptProjectLocked,
    AttemptProjectNotFound,
    AttemptUserNotFound,
)
from app.services.ai_check_limit_service import (
    MAX_AI_CHECKS_PER_PROJECT,
)


@dataclass(frozen=True)
class CreatedAttempt:
    id: int
    number: int
    xp_snapshot: int


@dataclass(frozen=True)
class AttemptListItem:
    id: int
    number: int
    status: str
    submitted_at: datetime
    xp_snapshot: int


@dataclass(frozen=True)
class ProjectAttemptsView:
    project_id: int
    project_number: int
    project_title: str
    course_slug: str
    attempts: list[AttemptListItem]


@dataclass(frozen=True)
class AttemptDetail:
    id: int
    project_id: int
    project_number: int
    project_title: str

    number: int
    filename: str
    source_code: str

    status: str
    xp_snapshot: int

    ai_feedback: str | None
    error_message: str | None

    submitted_at: datetime
    checked_at: datetime | None


async def create_attempt(
    telegram_user_id: int,
    project_id: int,
    filename: str,
    source_code: str,
) -> CreatedAttempt:
    async with async_session_factory() as session:
        user_repository = UserRepository(session)
        project_repository = ProjectRepository(
            session
        )
        attempt_repository = AttemptRepository(
            session
        )
        hint_repository = HintRepository(session)
        user_project_repository = (
            UserProjectRepository(session)
        )

        user = await user_repository.get_by_telegram_id(
            telegram_user_id
        )

        if user is None:
            raise AttemptUserNotFound

        project = await project_repository.get_by_id(
            project_id
        )

        if project is None:
            raise AttemptProjectNotFound

        if project.published_at is None:
            raise AttemptProjectLocked

        ai_checks_used = (
            await attempt_repository
            .count_ai_checks(
                user_id=user.id,
                project_id=project.id,
            )
        )

        if (
                ai_checks_used
                >= MAX_AI_CHECKS_PER_PROJECT
        ):
            raise AttemptAILimitReached(
                "Лимит AI-проверок "
                "для этого Project исчерпан."
            )

        await attempt_repository.lock_attempt_creation(
            user_id=user.id,
            project_id=project.id,
        )

        active_attempt = (
            await attempt_repository
            .get_active_for_project(
                user_id=user.id,
                project_id=project.id,
            )
        )

        if active_attempt is not None:
            raise AttemptAlreadyPending

        completed = (
            await user_project_repository
            .get_completed_project(
                user_id=user.id,
                project_id=project.id,
            )
        )

        if completed is not None:
            xp_snapshot = 0

        else:
            latest_hint = (
                await hint_repository
                .get_latest_published(
                    project.id
                )
            )

            if latest_hint is not None:
                xp_snapshot = (
                    latest_hint.xp_after_publish
                )
            else:
                xp_snapshot = project.max_xp

        attempt_number = (
            await attempt_repository
            .get_next_attempt_number(
                user_id=user.id,
                project_id=project.id,
            )
        )

        try:
            attempt = await attempt_repository.create(
                user_id=user.id,
                project_id=project.id,
                attempt_number=attempt_number,
                filename=filename,
                source_code=source_code,
                xp_snapshot=xp_snapshot,
                requirements_snapshot=(
                        project.ai_requirements or ""
                ),
            )

            await session.commit()

        except IntegrityError as error:
            await session.rollback()

            raise AttemptError(
                "Не удалось сохранить попытку "
                "из-за конфликта данных."
            ) from error

        return CreatedAttempt(
            id=attempt.id,
            number=attempt.attempt_number,
            xp_snapshot=attempt.xp_snapshot,
        )


async def get_project_attempts(
    telegram_user_id: int,
    project_id: int,
) -> ProjectAttemptsView | None:
    async with async_session_factory() as session:
        user_repository = UserRepository(session)
        project_repository = ProjectRepository(
            session
        )
        course_repository = CourseRepository(
            session
        )
        attempt_repository = AttemptRepository(
            session
        )

        user = await user_repository.get_by_telegram_id(
            telegram_user_id
        )

        if user is None:
            return None

        project = await project_repository.get_by_id(
            project_id
        )

        if project is None:
            return None

        course = await course_repository.get_by_id(
            project.course_id
        )

        if course is None:
            return None

        attempts = (
            await attempt_repository
            .get_by_project_for_user(
                user_id=user.id,
                project_id=project.id,
            )
        )

        return ProjectAttemptsView(
            project_id=project.id,
            project_number=project.number,
            project_title=project.title,
            course_slug=course.slug,
            attempts=[
                AttemptListItem(
                    id=attempt.id,
                    number=attempt.attempt_number,
                    status=attempt.status,
                    submitted_at=(
                        attempt.submitted_at
                    ),
                    xp_snapshot=(
                        attempt.xp_snapshot
                    ),
                )
                for attempt in attempts
            ],
        )


async def get_attempt_detail(
    telegram_user_id: int,
    attempt_id: int,
) -> AttemptDetail | None:
    async with async_session_factory() as session:
        user_repository = UserRepository(session)
        project_repository = ProjectRepository(
            session
        )
        attempt_repository = AttemptRepository(
            session
        )

        user = await user_repository.get_by_telegram_id(
            telegram_user_id
        )

        if user is None:
            return None

        attempt = (
            await attempt_repository
            .get_by_id_for_user(
                attempt_id=attempt_id,
                user_id=user.id,
            )
        )

        if attempt is None:
            return None

        project = await project_repository.get_by_id(
            attempt.project_id
        )

        if project is None:
            return None

        return AttemptDetail(
            id=attempt.id,
            project_id=project.id,
            project_number=project.number,
            project_title=project.title,
            number=attempt.attempt_number,
            filename=attempt.filename,
            source_code=attempt.source_code,
            status=attempt.status,
            xp_snapshot=attempt.xp_snapshot,
            ai_feedback=attempt.ai_feedback,
            error_message=attempt.error_message,
            submitted_at=attempt.submitted_at,
            checked_at=attempt.checked_at,
        )

async def save_attempt_status_message(
    attempt_id: int,
    chat_id: int,
    message_id: int,
) -> None:
    async with async_session_factory() as session:
        attempt_repository = AttemptRepository(
            session
        )

        attempt = await attempt_repository.get_by_id(
            attempt_id
        )

        if attempt is None:
            return

        await attempt_repository.set_status_message(
            attempt=attempt,
            chat_id=chat_id,
            message_id=message_id,
        )

        await session.commit()


async def mark_attempt_setup_error(
    attempt_id: int,
    error_message: str,
) -> None:
    async with async_session_factory() as session:
        attempt_repository = AttemptRepository(
            session
        )

        attempt = await attempt_repository.get_by_id(
            attempt_id
        )

        if (
            attempt is None
            or attempt.status != "pending"
        ):
            return

        await attempt_repository.mark_error(
            attempt=attempt,
            error_message=error_message,
        )

        await session.commit()