"""add ai review consent to users

Revision ID: f432b04cd0eb
Revises: 071bb6121074
Create Date: 2026-09-23 22:51:17.169419

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f432b04cd0eb"
down_revision: Union[str, Sequence[str], None] = "071bb6121074"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "ai_review_consent_version",
            sa.String(length=16),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "ai_review_consent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "users",
        "ai_review_consent_at",
    )

    op.drop_column(
        "users",
        "ai_review_consent_version",
    )
