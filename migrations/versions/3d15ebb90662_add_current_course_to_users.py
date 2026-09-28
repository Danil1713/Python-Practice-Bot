"""add current course to users

Revision ID: 3d15ebb90662
Revises: aef0699ba438
Create Date: 2026-09-28 19:25:14.194639

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d15ebb90662'
down_revision: Union[str, Sequence[str], None] = 'aef0699ba438'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "current_course_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_users_current_course_id_courses",
        "users",
        "courses",
        ["current_course_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_users_current_course_id",
        "users",
        ["current_course_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_users_current_course_id",
        table_name="users",
    )

    op.drop_constraint(
        "fk_users_current_course_id_courses",
        "users",
        type_="foreignkey",
    )

    op.drop_column(
        "users",
        "current_course_id",
    )
