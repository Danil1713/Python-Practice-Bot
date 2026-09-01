from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

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

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()