import re
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import validate_email_format

INSTAGRAM_HANDLE_REGEX = re.compile(r"^@?[a-zA-Z0-9._]{1,30}$")


class SocialAccountCreate(BaseModel):
    platform: Literal["facebook", "instagram"]
    name: str = Field(..., min_length=1, max_length=255)
    account_identifier: str = Field(..., min_length=1, max_length=255)
    email: str | None = None
    profile_picture_url: str | None = None
    access_token: str = Field(..., min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Account name cannot be blank.")
        return cleaned

    @field_validator("account_identifier")
    @classmethod
    def validate_identifier(cls, v: str, info) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Account identifier/username cannot be blank.")
        platform = info.data.get("platform")
        if platform == "instagram":
            if " " in cleaned or not INSTAGRAM_HANDLE_REGEX.match(cleaned):
                raise ValueError("Invalid Instagram handle. Must contain only letters, numbers, periods, and underscores.")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            return None
        return validate_email_format(cleaned)

    @field_validator("access_token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Access token cannot be blank.")
        return cleaned


class SocialAccountResponse(BaseModel):
    id: int
    user_id: int
    platform: str
    name: str
    account_identifier: str
    email: str | None
    profile_picture_url: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlatformDestination(BaseModel):
    platform: Literal["linkedin", "facebook", "instagram"]
    account_id: int


class MultiPublishRequest(BaseModel):
    post_id: int
    destinations: list[PlatformDestination] = Field(..., min_length=1)
    scheduled_at: datetime | None = None

    @field_validator("destinations")
    @classmethod
    def validate_destinations(cls, v: list[PlatformDestination]) -> list[PlatformDestination]:
        if not v:
            raise ValueError("Please select at least one destination platform to publish to.")
        return v
