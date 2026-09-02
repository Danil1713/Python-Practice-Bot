from dataclasses import dataclass
from datetime import datetime

from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.project_repository import (
    ProjectRepository,
)
from app.database.repositories.user_repository import (
    UserRepository,
)
from app.database.repositories.xp_repository import (
    XPRepository,
)
from app.database.session import (
    async_session_factory,
)


@dataclass(frozen=True)
class XPHistoryItem:
    amount: int
    reason: str
    project_number: int | None
    project_title: str | None
    created_at: datetime


@dataclass(frozen=True)
class CourseXPView:
    course_slug: str
    course_title: str
    total_xp: int
    history: list[XPHistoryItem]


async def get_course_xp(
    telegram_user_id: int,
    course_slug: str,
) -> CourseXPView | None:
    async with async_session_factory() as session:
        user_repository = UserRepository(session)
        course_repository = CourseRepository(session)
        project_repository = ProjectRepository(
            session
        )
        xp_repository = XPRepository(session)

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

        total_xp = (
            await xp_repository.get_total_by_course(
                user_id=user.id,
                course_id=course.id,
            )
        )

        transactions = (
            await xp_repository.get_recent_by_course(
                user_id=user.id,
                course_id=course.id,
                limit=10,
            )
        )

        history: list[XPHistoryItem] = []

        for transaction in transactions:
            project_number = None
            project_title = None

            if transaction.project_id is not None:
                project = (
                    await project_repository.get_by_id(
                        transaction.project_id
                    )
                )

                if project is not None:
                    project_number = project.number
                    project_title = project.title

            history.append(
                XPHistoryItem(
                    amount=transaction.amount,
                    reason=transaction.reason,
                    project_number=project_number,
                    project_title=project_title,
                    created_at=transaction.created_at,
                )
            )

        return CourseXPView(
            course_slug=course.slug,
            course_title=course.title,
            total_xp=total_xp,
            history=history,
        )