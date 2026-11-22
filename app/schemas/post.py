from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PostUpdate(BaseModel):
    content: str = Field(..., min_length=1)
    image_url: str | None = None

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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
