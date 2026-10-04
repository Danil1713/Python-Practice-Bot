"""add attempt evaluation metadata

Revision ID: aef0699ba438
Revises: f432b04cd0eb
Create Date: 2026-09-24 10:13:16.822848

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aef0699ba438"
down_revision: Union[str, Sequence[str], None] = "f432b04cd0eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attempts",
        sa.Column(
            "requirements_snapshot",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "attempts",
        sa.Column(
            "evaluation_version",
            sa.String(length=32),
            nullable=True,
        ),
    )

    op.add_column(
        "attempts",
        sa.Column(
            "ai_model",
            sa.String(length=128),
            nullable=True,
        ),
    )

    op.add_column(
        "attempts",
        sa.Column(
            "ai_policy_version",
            sa.String(length=32),
            nullable=True,
        ),
    )

    op.add_column(
        "attempts",
        sa.Column(
            "ai_result_json",
            sa.Text(),
            nullable=True,
        ),
    )

    op.drop_constraint(
        "ck_attempts_status",
        "attempts",
        type_="check",
    )

    op.create_check_constraint(
        "ck_attempts_status",
        "attempts",
        ("status IN ('pending', 'checking', 'passed', 'failed', 'review', 'error')"),
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE attempts
        SET status = 'error'
        WHERE status = 'review'
        """
    )

    op.drop_constraint(
        "ck_attempts_status",
        "attempts",
        type_="check",
    )

    op.create_check_constraint(
        "ck_attempts_status",
        "attempts",
        ("status IN ('pending', 'checking', 'passed', 'failed', 'error')"),
    )

    op.drop_column(
        "attempts",
        "ai_result_json",
    )

    op.drop_column(
        "attempts",
        "ai_policy_version",
    )

    op.drop_column(
        "attempts",
        "ai_model",
    )

    op.drop_column(
        "attempts",
        "evaluation_version",
    )

    op.drop_column(
        "attempts",
        "requirements_snapshot",
    )
