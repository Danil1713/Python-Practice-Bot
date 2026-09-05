from app.config import get_admin_telegram_ids


def is_admin(
    telegram_user_id: int,
) -> bool:
    return (
        telegram_user_id
        in get_admin_telegram_ids()
    )