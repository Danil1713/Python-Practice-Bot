from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class XPTransaction(Base):
    __tablename__ = "xp_transactions"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "project_id",
            "reason",
            name="uq_xp_user_project_reason",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_xp_transactions_amount_positive",
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

    project_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )