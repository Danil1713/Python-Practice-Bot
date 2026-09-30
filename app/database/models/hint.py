from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Hint(Base):
    __tablename__ = "hints"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "number",
            name="uq_hints_project_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    xp_after_publish: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
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
