from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    BigInteger,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Attempt(Base):
    __tablename__ = "attempts"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "project_id",
            "attempt_number",
            name="uq_attempts_user_project_number",
        ),
        CheckConstraint(
            "status IN "
            "('pending', 'checking', "
            "'passed', 'failed', "
            "'review', 'error')",
            name="ck_attempts_status",
        ),
        CheckConstraint(
            "attempt_number > 0",
            name="ck_attempts_attempt_number_positive",
        ),
        CheckConstraint(
            "xp_snapshot >= 0",
            name="ck_attempts_xp_snapshot_non_negative",
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

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    source_code: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
    )

    xp_snapshot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    requirements_snapshot: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    evaluation_version: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    ai_model: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    ai_policy_version: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    ai_result_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ai_feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    checking_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status_chat_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    status_message_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )