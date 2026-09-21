"""track attempt checking start

Revision ID: cc1e6b595c1a
Revises: 58639ae1ea3e
Create Date: 2026-09-13 19:06:24.743330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc1e6b595c1a'
down_revision: Union[str, Sequence[str], None] = '58639ae1ea3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attempts",
        sa.Column(
            "checking_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "attempts",
        "checking_started_at",
    )