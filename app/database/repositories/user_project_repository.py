from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.database.models.user_project import (
    UserProject,
)


class UserProjectRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_completed_project_ids(
        self,
        user_id: int,
        project_ids: list[int],
    ) -> set[int]:
        if not project_ids:
            return set()

        statement = select(
            UserProject.project_id
        ).where(
            UserProject.user_id == user_id,
            UserProject.project_id.in_(
                project_ids
            ),
        )

        result = await self.session.execute(
            statement
        )

        return set(
            result.scalars().all()
        )

    async def get_completed_project(
        self,
        user_id: int,
        project_id: int,
    ) -> UserProject | None:
        statement = select(
            UserProject
        ).where(
            UserProject.user_id == user_id,
            UserProject.project_id == project_id,
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def complete_project(
            self,
            user_id: int,
            project_id: int,
            awarded_xp: int,
    ) -> UserProject | None:
        statement = (
            insert(UserProject)
            .values(
                user_id=user_id,
                project_id=project_id,
                awarded_xp=awarded_xp,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    UserProject.user_id,
                    UserProject.project_id,
                ]
            )
            .returning(UserProject)
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()