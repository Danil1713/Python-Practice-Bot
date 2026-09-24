from aiogram import Router

from app.bot.handlers.attempts_history import (
    router as attempts_history_router,
)
from app.bot.handlers.attempts_submission import (
    router as attempts_submission_router,
)

router = Router()

router.include_router(
    attempts_submission_router
)

router.include_router(
    attempts_history_router
)