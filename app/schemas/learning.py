from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LearningCreate(BaseModel):
    topic: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    problem: str | None = None
    what_i_learned: str = Field(..., min_length=1)
    project: str | None = None
    lesson: str | None = None

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Topic cannot be blank or empty.")
        return cleaned

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Category cannot be blank or empty.")
        return cleaned

    @field_validator("what_i_learned")
    @classmethod
    def validate_what_i_learned(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("What You Learned cannot be blank or empty.")
        return cleaned

    @field_validator("problem", "project", "lesson")
    @classmethod
    def strip_optional_fields(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned if cleaned else None


class LearningResponse(LearningCreate):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
