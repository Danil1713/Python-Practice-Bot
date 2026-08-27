from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_database_url


engine = create_async_engine(
    get_database_url(),
    echo=False,
)


async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def check_database_connection() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))