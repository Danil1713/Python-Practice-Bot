from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database.models.project import Project


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