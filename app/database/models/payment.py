from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Payment(Base):
    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint(
            "provider = 'telegram_stars'",
            name="ck_payments_provider",
        ),
        CheckConstraint(
            "status IN ('pending', 'cancelled', 'review', 'succeeded')",
            name="ck_payments_status",
        ),
        CheckConstraint(
            "currency = 'XTR'",
            name="ck_payments_currency",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_payments_amount_positive",
        ),
        CheckConstraint(
            "subscription_days > 0",
            name="ck_payments_subscription_days_positive",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    course_id: Mapped[int] = mapped_column(
        ForeignKey(
            "courses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    external_payment_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="XTR",
    )

    subscription_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    pre_checkout_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
