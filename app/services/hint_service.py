from dataclasses import dataclass

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