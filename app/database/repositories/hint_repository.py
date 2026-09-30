from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.hint import Hint

HINT_CREATION_LOCK_NAMESPACE = -1002


class HintRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_by_project(
        self,
        project_id: int,
    ) -> list[Hint]:
        statement = (
            select(Hint).where(Hint.project_id == project_id).order_by(Hint.number)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def get_unpublished_by_project(
        self,
        project_id: int,
    ) -> list[Hint]:
        statement = (
            select(Hint)
            .where(
                Hint.project_id == project_id,
                Hint.published_at.is_(None),
            )
            .order_by(Hint.number)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def get_by_id(
        self,
        hint_id: int,
    ) -> Hint | None:
        statement = select(Hint).where(Hint.id == hint_id)

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_latest_published(
        self,
        project_id: int,
    ) -> Hint | None:
        statement = (
            select(Hint)
            .where(
                Hint.project_id == project_id,
                Hint.published_at.is_not(None),
            )
            .order_by(
                Hint.published_at.desc(),
                Hint.number.desc(),
            )
            .limit(1)
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def lock_creation(
        self,
        project_id: int,
    ) -> None:
        statement = select(
            func.pg_advisory_xact_lock(
                HINT_CREATION_LOCK_NAMESPACE,
                project_id,
            )
        )

        await self.session.execute(statement)

    async def get_next_number(
        self,
        project_id: int,
    ) -> int:
        statement = select(
            func.coalesce(
                func.max(Hint.number),
                0,
            )
        ).where(Hint.project_id == project_id)

        result = await self.session.execute(statement)

        current_max = result.scalar_one()

        return current_max + 1

    async def create(
        self,
        project_id: int,
        number: int,
        xp_after_publish: int,
    ) -> Hint:
        hint = Hint(
            project_id=project_id,
            number=number,
            xp_after_publish=xp_after_publish,
        )

        self.session.add(hint)

        await self.session.flush()

        return hint

    async def mark_published(
        self,
        hint: Hint,
        published_at: datetime,
        telegram_message_id: int,
    ) -> None:
        hint.published_at = published_at
        hint.telegram_message_id = telegram_message_id

        await self.session.flush()
