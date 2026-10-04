"""backfill payment subscription events

Revision ID: 6c9f2e7a4b13
Revises: d5e8c7a1b204

"""

from typing import Sequence, Union

from alembic import op

revision: str = "6c9f2e7a4b13"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "d5e8c7a1b204"
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
    op.execute(
        """
        INSERT INTO subscription_events (
            subscription_id,
            user_id,
            course_id,
            actor_telegram_id,
            event_type,
            source,
            reason,
            days,
            old_status,
            new_status,
            old_starts_at,
            new_starts_at,
            old_ends_at,
            new_ends_at,
            idempotency_key,
            created_at
        )
        SELECT
            s.id,
            p.user_id,
            p.course_id,
            u.telegram_id,
            'activate_or_extend',
            'payment',
            'telegram_stars_payment',
            p.subscription_days,
            NULL,
            'active',
            NULL,
            s.starts_at,
            NULL,
            s.ends_at,
            'payment:' || p.id::text,
            COALESCE(p.paid_at, p.created_at)
        FROM payments AS p
        JOIN subscriptions AS s
            ON s.user_id = p.user_id
           AND s.course_id = p.course_id
        JOIN users AS u
            ON u.id = p.user_id
        WHERE p.provider = 'telegram_stars'
          AND p.status = 'succeeded'
          AND NOT EXISTS (
              SELECT 1
              FROM subscription_events AS se
              WHERE se.idempotency_key = (
                  'payment:' || p.id::text
              )
          )
        """
    )


def downgrade() -> None:
    pass
