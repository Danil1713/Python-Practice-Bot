import asyncio
import logging

from aiogram import Bot

from app.services.channel_access_service import (
    get_expired_active_subscription_ids,
    revoke_expired_subscription_access,
)

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60
BATCH_SIZE = 50


async def process_expired_subscriptions(
    bot: Bot,
) -> int:
    subscription_ids = await get_expired_active_subscription_ids(limit=BATCH_SIZE)

    revoked_count = 0

    for subscription_id in subscription_ids:
        try:
            revoked = await revoke_expired_subscription_access(
                subscription_id=(subscription_id),
                bot=bot,
            )

            if revoked:
                revoked_count += 1

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Expired subscription processing failed subscription_id=%s",
                subscription_id,
            )

    return revoked_count


async def run_subscription_access_scheduler(
    bot: Bot,
) -> None:
    while True:
        try:
            revoked_count = await process_expired_subscriptions(bot)

            if revoked_count > 0:
                logger.info(
                    "Revoked %s expired subscription channel accesses",
                    revoked_count,
                )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception("Subscription access scheduler failed")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
