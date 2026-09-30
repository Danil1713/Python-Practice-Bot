from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.project import (
    Project,
)
from app.database.models.xp_transaction import (
    XPTransaction,
)


class XPRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def add_project_reward(
        self,
        user_id: int,
        course_id: int,
        project_id: int,
        amount: int,
    ) -> XPTransaction | None:
        statement = (
            insert(XPTransaction)
            .values(
                user_id=user_id,
                course_id=course_id,
                project_id=project_id,
                amount=amount,
                reason="project_completed",
            )
            .on_conflict_do_nothing(
                index_elements=[
                    XPTransaction.user_id,
                    XPTransaction.project_id,
                    XPTransaction.reason,
                ]
            )
            .returning(XPTransaction)
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_total_by_course(
        self,
        user_id: int,
        course_id: int,
    ) -> int:
        statement = select(
            func.coalesce(
                func.sum(XPTransaction.amount),
                0,
            )
        ).where(
            XPTransaction.user_id == user_id,
            XPTransaction.course_id == course_id,
        )

        result = await self.session.execute(statement)

        return int(result.scalar_one())

    async def get_recent_by_course(
        self,
        user_id: int,
        course_id: int,
        limit: int = 10,
    ) -> list[
        tuple[
            XPTransaction,
            int | None,
            str | None,
        ]
    ]:
        statement = (
            select(
                XPTransaction,
                Project.number,
                Project.title,
            )
            .outerjoin(
                Project,
                Project.id == XPTransaction.project_id,
            )
            .where(
                XPTransaction.user_id == user_id,
                XPTransaction.course_id == course_id,
            )
            .order_by(XPTransaction.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return [
            (
                transaction,
                project_number,
                project_title,
            )
            for (
                transaction,
                project_number,
                project_title,
            ) in result.all()
        ]
