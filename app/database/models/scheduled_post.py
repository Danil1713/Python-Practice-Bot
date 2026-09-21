from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    __table_args__ = (
        CheckConstraint(
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
            name=(
                "ck_scheduled_posts_"
                "entity_by_type"
            ),
        ),
        Index(
            "uq_scheduled_posts_active_project",
            "project_id",
            unique=True,
            postgresql_where=text(
                "project_id IS NOT NULL "
                "AND status IN "
                "('scheduled', 'publishing')"
            ),
        ),
        Index(
            "uq_scheduled_posts_active_hint",
            "hint_id",
            unique=True,
            postgresql_where=text(
                "hint_id IS NOT NULL "
                "AND status IN "
                "('scheduled', 'publishing')"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    course_id: Mapped[int] = mapped_column(
        ForeignKey(
            "courses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    post_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    project_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    hint_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "hints.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    publishing_started_at: Mapped[datetime | None] = (
        mapped_column(
            DateTime(timezone=True),
            nullable=True,
        )
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="scheduled",
        nullable=False,
        index=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    telegram_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )