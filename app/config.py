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

def get_openai_api_key() -> str:
    return get_required_env("OPENAI_API_KEY")

def get_gemini_api_key() -> str:
    return get_required_env("GEMINI_API_KEY")

def get_admin_telegram_ids() -> set[int]:
    raw_value = get_required_env(
        "ADMIN_TELEGRAM_IDS"
    )

    return {
        int(item.strip())
        for item in raw_value.split(",")
        if item.strip()
    }

def get_app_timezone() -> str:
    return os.getenv(
        "APP_TIMEZONE",
        "Europe/Moscow",
    )

def get_admin_username() -> str:
    return get_required_env(
        "ADMIN_USERNAME"
    ).lstrip("@")