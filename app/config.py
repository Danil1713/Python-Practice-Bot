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

def get_redis_url() -> str:
    return get_required_env(
        "REDIS_URL"
    )

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

def get_ai_model() -> str:
    return os.getenv(
        "AI_MODEL",
        "gemini-3.6-flash",
    )


def get_ai_timeout_seconds() -> float:
    value = float(
        os.getenv(
            "AI_TIMEOUT_SECONDS",
            "45",
        )
    )

    if value <= 0:
        raise RuntimeError(
            "AI_TIMEOUT_SECONDS "
            "должен быть больше 0"
        )

    return value


def get_ai_max_attempts() -> int:
    value = int(
        os.getenv(
            "AI_MAX_ATTEMPTS",
            "3",
        )
    )

    if value <= 0:
        raise RuntimeError(
            "AI_MAX_ATTEMPTS "
            "должен быть больше 0"
        )

    return value


def get_ai_retry_base_delay_seconds() -> float:
    value = float(
        os.getenv(
            "AI_RETRY_BASE_DELAY_SECONDS",
            "1",
        )
    )

    if value < 0:
        raise RuntimeError(
            "AI_RETRY_BASE_DELAY_SECONDS "
            "не может быть меньше 0"
        )

    return value


def get_ai_max_concurrency() -> int:
    value = int(
        os.getenv(
            "AI_MAX_CONCURRENCY",
            "2",
        )
    )

    if value <= 0:
        raise RuntimeError(
            "AI_MAX_CONCURRENCY "
            "должен быть больше 0"
        )

    return value