"""store attempt status message

Revision ID: 4fd611067312
Revises: 0816e7797b8e
Create Date: 2026-09-10 10:41:44.357293

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fd611067312'
down_revision: Union[str, Sequence[str], None] = '0816e7797b8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attempts",
        sa.Column(
            "status_chat_id",
            sa.BigInteger(),
            nullable=True,
        ),
    )

    op.add_column(
        "attempts",
        sa.Column(
            "status_message_id",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "attempts",
        "status_message_id",
    )

    op.drop_column(
        "attempts",
        "status_chat_id",
    )
