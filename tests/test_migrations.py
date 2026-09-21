import os

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import (
    create_async_engine,
)


@pytest.mark.asyncio
async def test_fresh_database_has_required_tables():
    database_url = os.environ[
        "DATABASE_URL"
    ]

    engine = create_async_engine(
        database_url
    )

    try:
        async with engine.connect() as connection:
            tables = await connection.run_sync(
                lambda sync_connection: set(
                    inspect(
                        sync_connection
                    ).get_table_names()
                )
            )

    finally:
        await engine.dispose()

    required_tables = {
        "users",
        "courses",
        "subscriptions",
        "subscription_events",
        "projects",
        "hints",
        "user_projects",
        "attempts",
        "xp_transactions",
        "scheduled_posts",
        "payments",
    }

    missing_tables = (
        required_tables - tables
    )

    assert not missing_tables, (
        "После alembic upgrade head "
        "не созданы таблицы: "
        f"{sorted(missing_tables)}"
    )


@pytest.mark.asyncio
async def test_xp_transactions_schema():
    database_url = os.environ[
        "DATABASE_URL"
    ]

    engine = create_async_engine(
        database_url
    )

    try:
        async with engine.connect() as connection:
            columns = await connection.run_sync(
                lambda sync_connection: {
                    column["name"]
                    for column in inspect(
                        sync_connection
                    ).get_columns(
                        "xp_transactions"
                    )
                }
            )

    finally:
        await engine.dispose()

    assert {
        "id",
        "user_id",
        "course_id",
        "project_id",
        "amount",
        "reason",
        "created_at",
    } <= columns