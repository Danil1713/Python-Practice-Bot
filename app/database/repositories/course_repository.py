from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.course import Course


class CourseRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_by_slug(
        self,
        slug: str,
    ) -> Course | None:
        statement = select(Course).where(
            Course.slug == slug,
            Course.is_active.is_(True),
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def get_all_active(
        self,
    ) -> list[Course]:
        statement = (
            select(Course)
            .where(
                Course.is_active.is_(True)
            )
            .order_by(Course.id)
        )

        result = await self.session.execute(
            statement
        )

        return list(
            result.scalars().all()
        )