"""allow system subscription events

Revision ID: d5e8c7a1b204
Revises: a4f7b29c6d10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e8c7a1b204"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "a4f7b29c6d10"
branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None
depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    op.alter_column(
        "subscription_events",
        "actor_telegram_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE subscription_events
        SET actor_telegram_id = 0
        WHERE actor_telegram_id IS NULL
        """
    )

    op.alter_column(
        "subscription_events",
        "actor_telegram_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
