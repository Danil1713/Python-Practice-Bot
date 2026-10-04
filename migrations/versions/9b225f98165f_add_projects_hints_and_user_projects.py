"""add projects hints and user projects

Revision ID: 9b225f98165f
Revises: 4a2e01582985
Create Date: 2026-08-28 10:38:54.585298

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9b225f98165f"
down_revision: Union[str, Sequence[str], None] = "4a2e01582985"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("max_xp", sa.Integer(), nullable=False),
        sa.Column("ai_requirements", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "number", name="uq_projects_course_number"),
    )
    op.create_index(
        op.f("ix_projects_course_id"), "projects", ["course_id"], unique=False
    )
    op.create_table(
        "hints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("xp_after_publish", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "number", name="uq_hints_project_number"),
    )
    op.create_index(op.f("ix_hints_project_id"), "hints", ["project_id"], unique=False)
    op.create_table(
        "user_projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("awarded_xp", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "project_id", name="uq_user_projects_user_project"
        ),
    )
    op.create_index(
        op.f("ix_user_projects_project_id"),
        "user_projects",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_projects_user_id"), "user_projects", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_projects_user_id"), table_name="user_projects")
    op.drop_index(op.f("ix_user_projects_project_id"), table_name="user_projects")
    op.drop_table("user_projects")
    op.drop_index(op.f("ix_hints_project_id"), table_name="hints")
    op.drop_table("hints")
    op.drop_index(op.f("ix_projects_course_id"), table_name="projects")
    op.drop_table("projects")
