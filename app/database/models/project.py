from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Project(Base):
    __tablename__ = "projects"

    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "number",
            name="uq_projects_course_number",
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

    number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    max_xp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )

    ai_requirements: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    telegram_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )