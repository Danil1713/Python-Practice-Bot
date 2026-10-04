"""validate scheduled post entities

Revision ID: 58639ae1ea3e
Revises: 7b3034dea638
Create Date: 2026-09-13 14:21:31.816323

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58639ae1ea3e"
down_revision: Union[str, Sequence[str], None] = "7b3034dea638"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE scheduled_posts
        SET project_id = NULL
        WHERE post_type = 'hint'
          AND hint_id IS NOT NULL
        """
    )

    op.create_check_constraint(
        "ck_scheduled_posts_entity_by_type",
        "scheduled_posts",
        (
            "("
            "post_type = 'regular' "
            "AND project_id IS NULL "
            "AND hint_id IS NULL"
            ") OR ("
            "post_type = 'project' "
            "AND project_id IS NOT NULL "
            "AND hint_id IS NULL"
            ") OR ("
            "post_type = 'hint' "
            "AND project_id IS NULL "
            "AND hint_id IS NOT NULL"
            ")"
        ),
    )

    op.create_index(
        "uq_scheduled_posts_active_project",
        "scheduled_posts",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text(
            "project_id IS NOT NULL AND status IN ('scheduled', 'publishing')"
        ),
    )

    op.create_index(
        "uq_scheduled_posts_active_hint",
        "scheduled_posts",
        ["hint_id"],
        unique=True,
        postgresql_where=sa.text(
            "hint_id IS NOT NULL AND status IN ('scheduled', 'publishing')"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_scheduled_posts_active_hint",
        table_name="scheduled_posts",
    )

    op.drop_index(
        "uq_scheduled_posts_active_project",
        table_name="scheduled_posts",
    )

    op.drop_constraint(
        "ck_scheduled_posts_entity_by_type",
        "scheduled_posts",
        type_="check",
    )
