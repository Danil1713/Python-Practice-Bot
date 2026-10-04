"""add subscription audit events

Revision ID: ab1416df282b
Revises: cc1e6b595c1a
Create Date: 2026-09-21 13:51:42.227391

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab1416df282b"
down_revision: Union[str, Sequence[str], None] = "cc1e6b595c1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscription_events",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "actor_telegram_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "days",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "old_status",
            sa.String(length=32),
            nullable=True,
        ),
        sa.Column(
            "new_status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "old_starts_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "new_starts_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "old_ends_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "new_ends_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
    )

    op.create_index(
        op.f("ix_subscription_events_subscription_id"),
        "subscription_events",
        ["subscription_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_subscription_events_user_id"),
        "subscription_events",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_subscription_events_course_id"),
        "subscription_events",
        ["course_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_subscription_events_idempotency_key"),
        "subscription_events",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_subscription_events_idempotency_key"),
        table_name="subscription_events",
    )

    op.drop_index(
        op.f("ix_subscription_events_course_id"),
        table_name="subscription_events",
    )

    op.drop_index(
        op.f("ix_subscription_events_user_id"),
        table_name="subscription_events",
    )

    op.drop_index(
        op.f("ix_subscription_events_subscription_id"),
        table_name="subscription_events",
    )

    op.drop_table("subscription_events")
