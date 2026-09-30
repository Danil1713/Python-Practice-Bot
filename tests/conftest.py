import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path

import asyncpg
import pytest
from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    pytest.exit(
        "TEST_DATABASE_URL не задан. Тесты остановлены.",
        returncode=2,
    )


test_url = make_url(TEST_DATABASE_URL)

test_database_name = test_url.database


if test_database_name is None or not test_database_name.endswith("_test"):
    pytest.exit(
        "TEST_DATABASE_URL должен указывать "
        "на отдельную БД с именем, "
        "заканчивающимся на _test.",
        returncode=2,
    )


if not re.fullmatch(
    r"[A-Za-z0-9_]+",
    test_database_name,
):
    pytest.exit(
        "Недопустимое имя тестовой БД.",
        returncode=2,
    )


os.environ["DATABASE_URL"] = TEST_DATABASE_URL


async def create_test_database() -> None:
    connection = await asyncpg.connect(
        user=test_url.username,
        password=test_url.password,
        host=test_url.host,
        port=test_url.port or 5432,
        database="postgres",
    )

    try:
        await connection.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = $1
              AND pid <> pg_backend_pid()
            """,
            test_database_name,
        )

        await connection.execute(f'DROP DATABASE IF EXISTS "{test_database_name}"')

        await connection.execute(f'CREATE DATABASE "{test_database_name}"')

    finally:
        await connection.close()


async def drop_test_database() -> None:
    connection = await asyncpg.connect(
        user=test_url.username,
        password=test_url.password,
        host=test_url.host,
        port=test_url.port or 5432,
        database="postgres",
    )

    try:
        await connection.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = $1
              AND pid <> pg_backend_pid()
            """,
            test_database_name,
        )

        await connection.execute(f'DROP DATABASE IF EXISTS "{test_database_name}"')

    finally:
        await connection.close()


@pytest.fixture(
    scope="session",
    autouse=True,
)
def migrated_test_database():
    asyncio.run(create_test_database())

    environment = os.environ.copy()

    environment["DATABASE_URL"] = TEST_DATABASE_URL

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            "head",
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
    )

    if result.returncode != 0:
        asyncio.run(drop_test_database())

        pytest.fail("alembic upgrade head не прошёл на чистой БД.")

    yield

    asyncio.run(drop_test_database())


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)

    connection = await engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    session = session_factory()

    try:
        yield session

    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()
