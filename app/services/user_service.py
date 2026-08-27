from app.database.models.user import User
from app.database.repositories.user_repository import UserRepository
from app.database.session import async_session_factory


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