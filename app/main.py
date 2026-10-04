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
from app.bot.handlers.channel_access import (
    router as channel_access_router,
)
from app.bot.handlers.courses import router as courses_router
from app.bot.handlers.hints import router as hints_router
from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.notifications import (
    router as notifications_router,
)
from app.bot.handlers.payments import router as payments_router
from app.bot.handlers.progress import router as progress_router
from app.bot.handlers.projects import router as projects_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.subscription import (
    router as subscription_router,
)
from app.bot.handlers.xp import router as xp_router
from app.config import get_bot_token, get_redis_url
from app.database.session import engine
from app.logging_config import setup_logging
from app.scheduler.attempt_checks import (
    run_attempt_check_worker,
)
from app.scheduler.payments import (
    run_payment_recovery,
)
from app.scheduler.publishing import (
    run_publishing_scheduler,
)
from app.scheduler.subscriptions import (
    run_subscription_access_scheduler,
)
from app.services.ai_service import close_ai_client

logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Starting application")

    bot = Bot(
        token=get_bot_token(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )

    storage = None
    background_tasks = []

    try:
        storage = RedisStorage.from_url(
            get_redis_url(),
            key_builder=DefaultKeyBuilder(
                prefix="python_practice_bot:v1",
            ),
            state_ttl=timedelta(hours=24),
            data_ttl=timedelta(hours=24),
        )

        await storage.redis.ping()

        dispatcher = Dispatcher(storage=storage)

        dispatcher.errors.register(global_error_handler)

        dispatcher.include_router(notifications_router)
        dispatcher.include_router(payments_router)
        dispatcher.include_router(subscription_router)
        dispatcher.include_router(channel_access_router)
        dispatcher.include_router(start_router)
        dispatcher.include_router(admin_router)
        dispatcher.include_router(courses_router)
        dispatcher.include_router(attempts_router)
        dispatcher.include_router(projects_router)
        dispatcher.include_router(hints_router)
        dispatcher.include_router(progress_router)
        dispatcher.include_router(xp_router)
        dispatcher.include_router(menu_router)

        await bot.delete_webhook(drop_pending_updates=False)

        background_tasks.append(asyncio.create_task(run_publishing_scheduler(bot)))

        background_tasks.append(asyncio.create_task(run_attempt_check_worker(bot)))

        background_tasks.append(asyncio.create_task(run_payment_recovery()))

        background_tasks.append(
            asyncio.create_task(run_subscription_access_scheduler(bot))
        )

        await dispatcher.start_polling(
            bot,
            close_bot_session=False,
        )

    finally:
        for task in background_tasks:
            task.cancel()

        if background_tasks:
            await asyncio.gather(
                *background_tasks,
                return_exceptions=True,
            )

        logger.info("Shutting down application")

        try:
            if storage is not None:
                await storage.close()
        finally:
            try:
                await close_ai_client()
            finally:
                try:
                    await engine.dispose()
                finally:
                    await bot.session.close()


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
