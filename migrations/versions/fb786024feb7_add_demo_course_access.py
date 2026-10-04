"""add demo course access

Revision ID: fb786024feb7
Revises: 9b225f98165f
Create Date: 2026-08-28 16:28:15.689982

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "fb786024feb7"
down_revision: Union[str, Sequence[str], None] = "9b225f98165f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "courses",
        sa.Column(
            "requires_subscription",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    courses_table = sa.table(
        "courses",
        sa.column("slug", sa.String()),
        sa.column("title", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("is_active", sa.Boolean()),
        sa.column("requires_subscription", sa.Boolean()),
    )

    op.bulk_insert(
        courses_table,
        [
            {
                "slug": "demo",
                "title": "🎮 Demo",
                "description": "Бесплатные демонстрационные проекты",
                "is_active": True,
                "requires_subscription": False,
            },
        ],
    )

    op.alter_column(
        "courses",
        "requires_subscription",
        server_default=None,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DELETE FROM courses WHERE slug = 'demo'"))
    op.drop_column("courses", "requires_subscription")
