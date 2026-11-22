from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True  # "facebook", "instagram", "linkedin"
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    account_identifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False  # e.g., Page ID or @username
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    profile_picture_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    encrypted_access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="social_accounts")
