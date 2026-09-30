import logging

from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)


async def global_error_handler(
    event: ErrorEvent,
) -> bool:
    update_id = None

    if event.update is not None:
        update_id = event.update.update_id

    logger.error(
        "Unhandled Telegram update error update_id=%s",
        update_id,
        exc_info=(
            type(event.exception),
            event.exception,
            event.exception.__traceback__,
        ),
    )

    return True
