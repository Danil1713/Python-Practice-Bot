"""track publishing start time

Revision ID: 709dc03cb450
Revises: f554747e3fb1
Create Date: 2026-09-03 19:01:32.713836

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "709dc03cb450"
down_revision: Union[str, Sequence[str], None] = "f554747e3fb1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "scheduled_posts",
        sa.Column("publishing_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("scheduled_posts", "publishing_started_at")
