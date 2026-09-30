from app.database.models.course import Course
from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.session import (
    async_session_factory,
)


async def get_course_by_slug(
    course_slug: str,
) -> Course | None:
    async with async_session_factory() as session:
        repository = CourseRepository(session)

        return await repository.get_by_slug(course_slug)


async def get_active_courses() -> list[Course]:
    async with async_session_factory() as session:
        repository = CourseRepository(session)

        return await repository.get_all_active()
