import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import (
    MemoryStorage,
)

from app.bot.handlers.courses import router as courses_router
from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.hints import router as hints_router
from app.bot.handlers.projects import router as projects_router
from app.bot.handlers.attempts import router as attempts_router
from app.bot.handlers.progress import router as progress_router
from app.bot.handlers.xp import router as xp_router
from app.database.session import engine
from app.scheduler.publishing import run_publishing_scheduler
from app.bot.handlers.admin import router as admin_router
from app.config import get_bot_token


async def main() -> None:
    bot = Bot(
        token=get_bot_token(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )

    scheduler_task = asyncio.create_task(
        run_publishing_scheduler(bot)
    )

    dispatcher = Dispatcher(
        storage=MemoryStorage()
    )

    dispatcher.include_router(admin_router)
    dispatcher.include_router(start_router)
    dispatcher.include_router(courses_router)
    dispatcher.include_router(attempts_router)
    dispatcher.include_router(projects_router)
    dispatcher.include_router(hints_router)
    dispatcher.include_router(progress_router)
    dispatcher.include_router(xp_router)
    dispatcher.include_router(menu_router)

    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dispatcher.start_polling(bot)

    finally:
        scheduler_task.cancel()

        try:
            await scheduler_task

        except asyncio.CancelledError:
            pass

        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())