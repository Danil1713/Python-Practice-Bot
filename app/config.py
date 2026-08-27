import os

from dotenv import load_dotenv


load_dotenv()


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Переменная окружения {name} не найдена"
        )

    return value


def get_bot_token() -> str:
    return get_required_env("BOT_TOKEN")


def get_database_url() -> str:
    return get_required_env("DATABASE_URL")