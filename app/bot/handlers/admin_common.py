from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram.types import CallbackQuery

from app.config import get_app_timezone
from app.services.admin_service import is_admin


async def check_admin(
    callback: CallbackQuery,
) -> bool:
    if is_admin(callback.from_user.id):
        return True

    await callback.answer(
        "⛔ Нет доступа.",
        show_alert=True,
    )

    return False


def format_admin_datetime(
    value: datetime,
) -> str:
    timezone = ZoneInfo(
        get_app_timezone()
    )

    local_value = value.astimezone(
        timezone
    )

    return local_value.strftime(
        "%d.%m.%Y %H:%M"
    )