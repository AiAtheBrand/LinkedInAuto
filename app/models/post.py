import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base


class JSONList(TypeDecorator):
    """Stores a list of strings as JSON in a TEXT column, deserializing to a Python list."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if not value:
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
            return [parsed]
        except Exception:
            return []


class Post(Base):

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    learning_id: Mapped[int] = mapped_column(
        ForeignKey("learnings.id"),
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        nullable=False
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    image_urls: Mapped[list[str]] = mapped_column(
        JSONList,
        default=list,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    learning = relationship("Learning")
    user = relationship("User", back_populates="posts")

    def get_image_urls(self) -> list[str]:
        if self.image_urls and isinstance(self.image_urls, list) and len(self.image_urls) > 0:
            return list(self.image_urls)
        if self.image_url:
            return [self.image_url]
        return []

    def set_image_urls(self, urls: list[str]) -> None:
        self.image_urls = list(urls) if urls else []
        self.image_url = urls[0] if urls else None
