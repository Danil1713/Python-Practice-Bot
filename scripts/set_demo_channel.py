import asyncio

from aiogram import Bot

from app.config import get_bot_token
from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.session import (
    async_session_factory,
    engine,
)

DEMO_CHANNEL = "@pythonpractice_demo"


async def main() -> None:
    bot = Bot(
        token=get_bot_token()
    )

    try:
        chat = await bot.get_chat(
            DEMO_CHANNEL
        )

        async with async_session_factory() as session:
            repository = CourseRepository(
                session
            )

            course = await repository.get_by_slug(
                "demo"
            )

            if course is None:
                raise RuntimeError(
                    "Demo course not found"
                )

            course.telegram_channel_id = chat.id

            await session.commit()

        print(
            f"Demo channel ID: {chat.id}"
        )

    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())