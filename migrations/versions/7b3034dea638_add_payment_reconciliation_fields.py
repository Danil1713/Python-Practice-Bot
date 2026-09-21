"""add payment reconciliation fields

Revision ID: 7b3034dea638
Revises: 4fd611067312
Create Date: 2026-09-11 20:15:41.636889

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b3034dea638'
down_revision: Union[str, Sequence[str], None] = '4fd611067312'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column(
            "pre_checkout_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "payments",
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "payments",
        "error_message",
    )

    op.drop_column(
        "payments",
        "pre_checkout_at",
    )
