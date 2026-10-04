"""restore missing revision

Revision ID: 8b3154cefc2c
Revises: f62fc49b05d5
"""

from typing import Sequence, Union

revision: str = "8b3154cefc2c"
down_revision: Union[str, Sequence[str], None] = "f62fc49b05d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
