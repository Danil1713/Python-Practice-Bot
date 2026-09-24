"""add domain constraints

Revision ID: 071bb6121074
Revises: ab1416df282b
Create Date: 2026-09-23 09:32:00.954042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '071bb6121074'
down_revision: Union[str, Sequence[str], None] = 'ab1416df282b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_attempts_status",
        "attempts",
        (
            "status IN "
            "('pending', 'checking', "
            "'passed', 'failed', 'error')"
        ),
    )

    op.create_check_constraint(
        "ck_attempts_attempt_number_positive",
        "attempts",
        "attempt_number > 0",
    )

    op.create_check_constraint(
        "ck_attempts_xp_snapshot_non_negative",
        "attempts",
        "xp_snapshot >= 0",
    )

    op.create_check_constraint(
        "ck_payments_provider",
        "payments",
        "provider = 'telegram_stars'",
    )

    op.create_check_constraint(
        "ck_payments_status",
        "payments",
        (
            "status IN "
            "('pending', 'cancelled', "
            "'review', 'succeeded')"
        ),
    )

    op.create_check_constraint(
        "ck_payments_currency",
        "payments",
        "currency = 'XTR'",
    )

    op.create_check_constraint(
        "ck_payments_amount_positive",
        "payments",
        "amount > 0",
    )

    op.create_check_constraint(
        "ck_payments_subscription_days_positive",
        "payments",
        "subscription_days > 0",
    )

    op.create_check_constraint(
        "ck_scheduled_posts_post_type",
        "scheduled_posts",
        (
            "post_type IN "
            "('regular', 'project', 'hint')"
        ),
    )

    op.create_check_constraint(
        "ck_scheduled_posts_status",
        "scheduled_posts",
        (
            "status IN "
            "('scheduled', 'publishing', "
            "'published', 'failed', 'cancelled')"
        ),
    )

    op.create_check_constraint(
        "ck_subscriptions_status",
        "subscriptions",
        "status IN ('active', 'cancelled')",
    )

    op.create_check_constraint(
        "ck_subscriptions_dates",
        "subscriptions",
        "ends_at > starts_at",
    )

    op.create_check_constraint(
        "ck_xp_transactions_amount_positive",
        "xp_transactions",
        "amount > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_xp_transactions_amount_positive",
        "xp_transactions",
        type_="check",
    )

    op.drop_constraint(
        "ck_subscriptions_dates",
        "subscriptions",
        type_="check",
    )

    op.drop_constraint(
        "ck_subscriptions_status",
        "subscriptions",
        type_="check",
    )

    op.drop_constraint(
        "ck_scheduled_posts_status",
        "scheduled_posts",
        type_="check",
    )

    op.drop_constraint(
        "ck_scheduled_posts_post_type",
        "scheduled_posts",
        type_="check",
    )

    op.drop_constraint(
        "ck_payments_subscription_days_positive",
        "payments",
        type_="check",
    )

    op.drop_constraint(
        "ck_payments_amount_positive",
        "payments",
        type_="check",
    )

    op.drop_constraint(
        "ck_payments_currency",
        "payments",
        type_="check",
    )

    op.drop_constraint(
        "ck_payments_status",
        "payments",
        type_="check",
    )

    op.drop_constraint(
        "ck_payments_provider",
        "payments",
        type_="check",
    )

    op.drop_constraint(
        "ck_attempts_xp_snapshot_non_negative",
        "attempts",
        type_="check",
    )

    op.drop_constraint(
        "ck_attempts_attempt_number_positive",
        "attempts",
        type_="check",
    )

    op.drop_constraint(
        "ck_attempts_status",
        "attempts",
        type_="check",
    )
