import asyncio
import logging
from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import (
    DefaultKeyBuilder,
)
from aiogram.fsm.storage.redis import (
    RedisStorage,
)

from app.bot.error_handler import global_error_handler
from app.bot.handlers.admin import router as admin_router
from app.bot.handlers.attempts import router as attempts_router
from app.bot.handlers.courses import router as courses_router
from app.bot.handlers.hints import router as hints_router
from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.payments import router as payments_router
from app.bot.handlers.progress import router as progress_router
from app.bot.handlers.projects import router as projects_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.subscription import router as subscription_router
from app.bot.handlers.xp import router as xp_router
from app.config import get_bot_token, get_redis_url
from app.database.session import engine
from app.logging_config import setup_logging
from app.scheduler.attempt_checks import run_attempt_check_worker
from app.scheduler.payments import run_payment_recovery
from app.scheduler.publishing import run_publishing_scheduler
from app.services.ai_service import close_ai_client

logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info(
        "Starting application"
    )

    bot = Bot(
        token=get_bot_token(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )

    storage = RedisStorage.from_url(
        get_redis_url(),
        key_builder=DefaultKeyBuilder(
            prefix="python_practice_bot:v1",
        ),
        state_ttl=timedelta(
            hours=24
        ),
        data_ttl=timedelta(
            hours=24
        ),
    )

    await storage.redis.ping()

    scheduler_task = asyncio.create_task(
        run_publishing_scheduler(bot)
    )

    attempt_worker_task = asyncio.create_task(
        run_attempt_check_worker(bot)
    )

    payment_recovery_task = asyncio.create_task(
        run_payment_recovery()
    )

    dispatcher = Dispatcher(
        storage=storage
    )

    dispatcher.errors.register(
        global_error_handler
    )

    dispatcher.include_router(payments_router)
    dispatcher.include_router(subscription_router)
    dispatcher.include_router(start_router)
    dispatcher.include_router(admin_router)
    dispatcher.include_router(courses_router)
    dispatcher.include_router(attempts_router)
    dispatcher.include_router(projects_router)
    dispatcher.include_router(hints_router)
    dispatcher.include_router(progress_router)
    dispatcher.include_router(xp_router)
    dispatcher.include_router(menu_router)

    await bot.delete_webhook(
        drop_pending_updates=False
    )

    try:
        await dispatcher.start_polling(bot)


    finally:

        scheduler_task.cancel()
        attempt_worker_task.cancel()
        payment_recovery_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        try:
            await attempt_worker_task
        except asyncio.CancelledError:
            pass

        try:
            await payment_recovery_task
        except asyncio.CancelledError:
            pass

        logger.info(
            "Shutting down application"
        )

        await storage.close()
        await close_ai_client()
        await engine.dispose()


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())