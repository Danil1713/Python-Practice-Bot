from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    slug: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    telegram_channel_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )