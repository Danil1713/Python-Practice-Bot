"""make course channel unique

Revision ID: e8c6a44f2d91
Revises: 3d15ebb90662
Create Date: 2026-09-30 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "e8c6a44f2d91"
down_revision: Union[str, Sequence[str], None] = "3d15ebb90662"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_courses_telegram_channel_id",
        "courses",
        ["telegram_channel_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_courses_telegram_channel_id",
        "courses",
        type_="unique",
    )
