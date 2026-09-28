from datetime import datetime

from sqlalchemy import or_, select
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

    async def get_by_id(
            self,
            user_id: int,
    ) -> User | None:
        statement = select(User).where(
            User.id == user_id
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def search(
            self,
            value: str,
    ) -> list[User]:
        clean_value = value.strip().lstrip("@")

        conditions = []

        if clean_value.isdigit():
            conditions.append(
                User.telegram_id == int(clean_value)
            )
        else:
            conditions.append(
                User.username.ilike(
                    clean_value
                )
            )

        statement = (
            select(User)
            .where(
                or_(*conditions)
            )
            .order_by(User.id)
            .limit(20)
        )

        result = await self.session.execute(
            statement
        )

        return list(
            result.scalars().all()
        )

    async def set_ai_review_consent(
            self,
            *,
            telegram_id: int,
            version: str,
            accepted_at: datetime,
    ) -> bool:
        user = await self.get_by_telegram_id(
            telegram_id
        )

        if user is None:
            return False

        user.ai_review_consent_version = version
        user.ai_review_consent_at = accepted_at

        return True

    async def set_current_course_id(
            self,
            *,
            telegram_id: int,
            course_id: int | None,
    ) -> bool:
        user = await self.get_by_telegram_id(
            telegram_id
        )

        if user is None:
            return False

        user.current_course_id = course_id

        await self.session.flush()

        return True