"""add attempts

Revision ID: f62fc49b05d5
Revises: fb786024feb7
Create Date: 2026-08-29 13:23:31.545357

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f62fc49b05d5"
down_revision: Union[str, Sequence[str], None] = "fb786024feb7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("xp_snapshot", sa.Integer(), nullable=False),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "project_id",
            "attempt_number",
            name="uq_attempts_user_project_number",
        ),
    )
    op.create_index(
        op.f("ix_attempts_project_id"), "attempts", ["project_id"], unique=False
    )
    op.create_index(op.f("ix_attempts_status"), "attempts", ["status"], unique=False)
    op.create_index(op.f("ix_attempts_user_id"), "attempts", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_attempts_user_id"), table_name="attempts")
    op.drop_index(op.f("ix_attempts_status"), table_name="attempts")
    op.drop_index(op.f("ix_attempts_project_id"), table_name="attempts")
    op.drop_table("attempts")
