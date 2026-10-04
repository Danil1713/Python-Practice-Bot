"""create missing xp transactions table

Revision ID: 0816e7797b8e
Revises: 3258dfb55987
Create Date: 2026-09-10 09:44:54.115280

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0816e7797b8e"
down_revision: Union[str, Sequence[str], None] = "3258dfb55987"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("xp_transactions"):
        op.create_table(
            "xp_transactions",
            sa.Column(
                "id",
                sa.Integer(),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.Integer(),
                nullable=False,
            ),
            sa.Column(
                "course_id",
                sa.Integer(),
                nullable=False,
            ),
            sa.Column(
                "project_id",
                sa.Integer(),
                nullable=True,
            ),
            sa.Column(
                "amount",
                sa.Integer(),
                nullable=False,
            ),
            sa.Column(
                "reason",
                sa.String(length=64),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["course_id"],
                ["courses.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["project_id"],
                ["projects.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint(
                "id",
            ),
            sa.UniqueConstraint(
                "user_id",
                "project_id",
                "reason",
                name="uq_xp_user_project_reason",
            ),
        )

        op.create_index(
            "ix_xp_transactions_user_id",
            "xp_transactions",
            ["user_id"],
            unique=False,
        )

        op.create_index(
            "ix_xp_transactions_course_id",
            "xp_transactions",
            ["course_id"],
            unique=False,
        )

        op.create_index(
            "ix_xp_transactions_project_id",
            "xp_transactions",
            ["project_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("xp_transactions"):
        op.drop_table("xp_transactions")
