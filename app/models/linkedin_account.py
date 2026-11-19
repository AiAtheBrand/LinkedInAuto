from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LinkedInAccount(Base):

    __tablename__ = "linkedin_accounts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    linkedin_member_urn: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
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

    encrypted_refresh_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    scopes: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="w_member_social,openid,profile,email"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="linkedin_accounts")

    __table_args__ = (
        UniqueConstraint("user_id", "linkedin_member_urn", name="uq_user_linkedin_member"),
    )
