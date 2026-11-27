import json
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PostUpdate(BaseModel):
    content: str = Field(..., min_length=1)
    image_url: str | None = None
    image_urls: list[str] | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Post content cannot be blank or empty.")
        return cleaned


class PostResponse(BaseModel):
    id: int
    user_id: int
    learning_id: int
    content: str
    status: str
    image_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    created_at: datetime

    @field_validator("image_urls", mode="before")
    @classmethod
    def parse_image_urls(cls, v: Any, info) -> list[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str) and v.strip():
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [v]
        return []

    model_config = ConfigDict(from_attributes=True)
