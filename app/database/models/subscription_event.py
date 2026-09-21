from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.database.base import Base


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey(
            "subscriptions.id",
        ),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
        ),
        nullable=False,
        index=True,
    )

    course_id: Mapped[int] = mapped_column(
        ForeignKey(
            "courses.id",
        ),
        nullable=False,
        index=True,
    )

    actor_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    old_status: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    new_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    old_starts_at: Mapped[datetime | None] = (
        mapped_column(
            DateTime(timezone=True),
            nullable=True,
        )
    )

    new_starts_at: Mapped[datetime] = (
        mapped_column(
            DateTime(timezone=True),
            nullable=False,
        )
    )

    old_ends_at: Mapped[datetime | None] = (
        mapped_column(
            DateTime(timezone=True),
            nullable=True,
        )
    )

    new_ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )