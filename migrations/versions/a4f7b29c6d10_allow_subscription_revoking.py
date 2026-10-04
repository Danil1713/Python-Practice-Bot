"""allow subscription revoking

Revision ID: a4f7b29c6d10
Revises: e8c6a44f2d91
Create Date: 2026-09-30 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "a4f7b29c6d10"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "e8c6a44f2d91"
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
    op.drop_constraint(
        "ck_subscriptions_status",
        "subscriptions",
        type_="check",
    )

    op.create_check_constraint(
        "ck_subscriptions_status",
        "subscriptions",
        ("status IN ('active', 'revoking', 'cancelled')"),
    )


def downgrade() -> None:
    op.execute("UPDATE subscriptions SET status = 'active' WHERE status = 'revoking'")

    op.drop_constraint(
        "ck_subscriptions_status",
        "subscriptions",
        type_="check",
    )

    op.create_check_constraint(
        "ck_subscriptions_status",
        "subscriptions",
        "status IN ('active', 'cancelled')",
    )
