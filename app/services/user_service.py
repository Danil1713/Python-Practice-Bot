from app.database.models.user import User
from app.database.repositories.user_repository import UserRepository
from app.database.session import async_session_factory
from datetime import UTC, datetime

AI_REVIEW_CONSENT_VERSION = "v1"


async def register_or_update_user(
    telegram_id: int,
    username: str | None,
    first_name: str,
) -> User:
    async with async_session_factory() as session:
        repository = UserRepository(session)

        user = await repository.upsert_telegram_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )

        await session.commit()

        return user

async def has_current_ai_review_consent(
    telegram_id: int,
) -> bool:
    async with async_session_factory() as session:
        repository = UserRepository(
            session
        )

        user = await repository.get_by_telegram_id(
            telegram_id
        )

        if user is None:
            return False

        return (
            user.ai_review_consent_version
            == AI_REVIEW_CONSENT_VERSION
            and user.ai_review_consent_at
            is not None
        )


async def accept_ai_review_consent(
    telegram_id: int,
) -> bool:
    async with async_session_factory() as session:
        repository = UserRepository(
            session
        )

        accepted = (
            await repository.set_ai_review_consent(
                telegram_id=telegram_id,
                version=(
                    AI_REVIEW_CONSENT_VERSION
                ),
                accepted_at=datetime.now(UTC),
            )
        )

        if not accepted:
            await session.rollback()
            return False

        await session.commit()

        return True