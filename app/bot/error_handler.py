import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)

EXPECTED_TELEGRAM_BAD_REQUESTS = (
    "message is not modified",
    "query is too old",
    "query id is invalid",
)


def is_expected_telegram_bad_request(
    exception: Exception,
) -> bool:
    if not isinstance(exception, TelegramBadRequest):
        return False

    message = exception.message.lower()

    return any(
        expected_message in message
        for expected_message in EXPECTED_TELEGRAM_BAD_REQUESTS
    )


async def global_error_handler(
    event: ErrorEvent,
) -> bool:
    update_id = None

    if event.update is not None:
        update_id = event.update.update_id

    if is_expected_telegram_bad_request(event.exception):
        logger.warning(
            "Ignored expected Telegram error update_id=%s error=%s",
            update_id,
            event.exception.message,
        )
        return True

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
