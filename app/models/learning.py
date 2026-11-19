from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Learning(Base):

    __tablename__ = "learnings"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    topic: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    problem: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )

    what_i_learned: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    project: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )

    lesson: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="learnings")
