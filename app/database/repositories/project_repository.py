from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.project import Project

PROJECT_CREATION_LOCK_NAMESPACE = -1001


class ProjectRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_by_course(
        self,
        course_id: int,
    ) -> list[Project]:
        statement = (
            select(Project)
            .where(
                Project.course_id == course_id
            )
            .order_by(Project.number)
        )

        result = await self.session.execute(
            statement
        )

        return list(
            result.scalars().all()
        )

    async def get_unpublished_by_course(
        self,
        course_id: int,
    ) -> list[Project]:
        statement = (
            select(Project)
            .where(
                Project.course_id == course_id,
                Project.published_at.is_(None),
            )
            .order_by(Project.number)
        )

        result = await self.session.execute(
            statement
        )

        return list(
            result.scalars().all()
        )

    async def get_available_for_hint_by_course(
            self,
            course_id: int,
    ) -> list[Project]:
        statement = (
            select(Project)
            .where(
                Project.course_id == course_id,
                Project.published_at.is_not(None),
            )
            .order_by(Project.number)
        )

        result = await self.session.execute(
            statement
        )

        return list(
            result.scalars().all()
        )

    async def get_by_id(
        self,
        project_id: int,
    ) -> Project | None:
        statement = select(Project).where(
            Project.id == project_id
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def lock_creation(
        self,
        course_id: int,
    ) -> None:
        statement = select(
            func.pg_advisory_xact_lock(
                PROJECT_CREATION_LOCK_NAMESPACE,
                course_id,
            )
        )

        await self.session.execute(
            statement
        )

    async def get_next_number(
        self,
        course_id: int,
    ) -> int:
        statement = select(
            func.coalesce(
                func.max(Project.number),
                0,
            )
        ).where(
            Project.course_id == course_id
        )

        result = await self.session.execute(
            statement
        )

        current_max = result.scalar_one()

        return current_max + 1

    async def create(
        self,
        course_id: int,
        number: int,
        title: str,
        ai_requirements: str,
    ) -> Project:
        project = Project(
            course_id=course_id,
            number=number,
            title=title,
            ai_requirements=ai_requirements,
        )

        self.session.add(project)

        await self.session.flush()

        return project

    async def mark_published(
        self,
        project: Project,
        published_at: datetime,
        telegram_message_id: int,
    ) -> None:
        project.published_at = published_at
        project.telegram_message_id = (
            telegram_message_id
        )

        await self.session.flush()