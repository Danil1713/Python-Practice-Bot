from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

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
)
from app.services.telegram_link_service import (
    build_channel_message_url,
)

HINT_XP_AFTER_PUBLISH_BY_NUMBER = {
    1: 80,
    2: 60,
    3: 40,
}


async def can_create_hint(
    project_id: int,
) -> bool:
    async with async_session_factory() as session:
        project_repository = ProjectRepository(
            session
        )
        hint_repository = HintRepository(
            session
        )

        project = await project_repository.get_by_id(
            project_id
        )

        if (
            project is None
            or project.published_at is None
        ):
            return False

        next_number = (
            await hint_repository.get_next_number(
                project_id
            )
        )

        return (
            next_number
            in HINT_XP_AFTER_PUBLISH_BY_NUMBER
        )


@dataclass(frozen=True)
class HintListItem:
    id: int
    number: int
    is_published: bool
    telegram_url: str | None

@dataclass(frozen=True)
class HintOpenView:
    id: int
    course_slug: str
    is_published: bool
    telegram_url: str | None


@dataclass(frozen=True)
class ProjectHintsView:
    project_id: int
    project_number: int
    project_title: str
    course_slug: str
    hints: list[HintListItem]


class HintCreationError(Exception):
    pass


@dataclass(frozen=True)
class CreatedHint:
    id: int
    number: int
    project_id: int
    xp_after_publish: int


async def get_project_hints(
    project_id: int,
) -> ProjectHintsView | None:
    async with async_session_factory() as session:
        project_repository = ProjectRepository(
            session
        )
        course_repository = CourseRepository(
            session
        )
        hint_repository = HintRepository(
            session
        )

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

        hints = await hint_repository.get_by_project(
            project.id
        )

        return ProjectHintsView(
            project_id=project.id,
            project_number=project.number,
            project_title=project.title,
            course_slug=course.slug,
            hints=[
                HintListItem(
                    id=hint.id,
                    number=hint.number,
                    is_published=(
                            hint.published_at
                            is not None
                    ),
                    telegram_url=(
                        build_channel_message_url(
                            channel_id=course.telegram_channel_id,
                            message_id=hint.telegram_message_id,
                        )
                        if (
                                hint.published_at is not None
                                and hint.telegram_message_id is not None
                                and course.telegram_channel_id is not None
                        )
                        else None
                    ),
                )
                for hint in hints
            ],
        )

async def get_hint_open_view(
    hint_id: int,
) -> HintOpenView | None:
    async with async_session_factory() as session:
        hint_repository = HintRepository(
            session
        )
        project_repository = ProjectRepository(
            session
        )
        course_repository = CourseRepository(
            session
        )

        hint = await hint_repository.get_by_id(
            hint_id
        )

        if hint is None:
            return None

        project = await project_repository.get_by_id(
            hint.project_id
        )

        if project is None:
            return None

        course = await course_repository.get_by_id(
            project.course_id
        )

        if course is None:
            return None

        telegram_url = None

        if (
            hint.published_at is not None
            and hint.telegram_message_id is not None
            and course.telegram_channel_id is not None
        ):
            telegram_url = (
                build_channel_message_url(
                    channel_id=(
                        course.telegram_channel_id
                    ),
                    message_id=(
                        hint.telegram_message_id
                    ),
                )
            )

        return HintOpenView(
            id=hint.id,
            course_slug=course.slug,
            is_published=(
                hint.published_at is not None
            ),
            telegram_url=telegram_url,
        )


async def create_hint(
    course_slug: str,
    project_id: int,
) -> CreatedHint:
    async with async_session_factory() as session:
        course_repository = CourseRepository(
            session
        )
        project_repository = ProjectRepository(
            session
        )
        hint_repository = HintRepository(
            session
        )

        course = await course_repository.get_by_slug(
            course_slug
        )

        if course is None:
            raise HintCreationError(
                "Курс не найден или недоступен."
            )

        project = await project_repository.get_by_id(
            project_id
        )

        if project is None:
            raise HintCreationError(
                "Проект не найден."
            )

        if project.course_id != course.id:
            raise HintCreationError(
                "Проект не относится к текущему курсу."
            )

        if project.published_at is None:
            raise HintCreationError(
                "Сначала опубликуй Project."
            )

        await hint_repository.lock_creation(
            project.id
        )

        number = await hint_repository.get_next_number(
            project.id
        )

        xp_after_publish = (
            HINT_XP_AFTER_PUBLISH_BY_NUMBER.get(
                number
            )
        )

        if xp_after_publish is None:
            raise HintCreationError(
                f"Для Hint {number} не настроено "
                "значение XP."
            )

        if xp_after_publish > project.max_xp:
            raise HintCreationError(
                "XP подсказки не может превышать "
                "максимальный XP проекта."
            )

        try:
            hint = await hint_repository.create(
                project_id=project.id,
                number=number,
                xp_after_publish=xp_after_publish,
            )

            await session.commit()

        except IntegrityError as error:
            await session.rollback()

            raise HintCreationError(
                "Не удалось создать подсказку "
                "из-за конфликта данных."
            ) from error

        return CreatedHint(
            id=hint.id,
            number=hint.number,
            project_id=hint.project_id,
            xp_after_publish=hint.xp_after_publish,
        )