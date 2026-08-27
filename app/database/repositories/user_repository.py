from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_telegram_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str,
    ) -> User:
        statement = (
            insert(User)
            .values(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            .on_conflict_do_update(
                index_elements=[User.telegram_id],
                set_={
                    "username": username,
                    "first_name": first_name,
                },
            )
            .returning(User)
        )

        result = await self.session.execute(statement)

        return result.scalar_one()

    async def get_by_telegram_id(
        self,
        telegram_id: int,
    ) -> User | None:
        statement = select(User).where(
            User.telegram_id == telegram_id
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()