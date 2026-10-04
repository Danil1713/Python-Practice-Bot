import os

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import (
    create_async_engine,
)


@pytest.mark.asyncio
async def test_fresh_database_has_required_tables():
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            tables = await connection.run_sync(
                lambda sync_connection: set(inspect(sync_connection).get_table_names())
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

    missing_tables = required_tables - tables

    assert not missing_tables, (
        f"После alembic upgrade head не созданы таблицы: {sorted(missing_tables)}"
    )


@pytest.mark.asyncio
async def test_xp_transactions_schema():
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            columns = await connection.run_sync(
                lambda sync_connection: {
                    column["name"]
                    for column in inspect(sync_connection).get_columns(
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


@pytest.mark.asyncio
async def test_course_channel_id_is_unique():
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            constraints = await connection.run_sync(
                lambda sync_connection: {
                    constraint["name"]
                    for constraint in inspect(sync_connection).get_unique_constraints(
                        "courses"
                    )
                }
            )

    finally:
        await engine.dispose()

    assert "uq_courses_telegram_channel_id" in constraints


@pytest.mark.asyncio
async def test_subscription_event_actor_can_be_null():
    database_url = os.environ["DATABASE_URL"]

    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            columns = await connection.run_sync(
                lambda sync_connection: {
                    column["name"]: column
                    for column in inspect(sync_connection).get_columns(
                        "subscription_events"
                    )
                }
            )

    finally:
        await engine.dispose()

    assert columns["actor_telegram_id"]["nullable"] is True
