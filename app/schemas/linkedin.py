from datetime import datetime
from pydantic import BaseModel, ConfigDict


class LinkedInAccountResponse(BaseModel):
    id: int
    linkedin_member_urn: str
    name: str
    email: str | None
    profile_picture_url: str | None
    scopes: str
    token_expires_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OAuthUrlResponse(BaseModel):
    authorization_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


class PublicationCreate(BaseModel):
    post_id: int
    linkedin_account_id: int
    scheduled_at: datetime | None = None


class PublicationResponse(BaseModel):
    id: int
    user_id: int
    post_id: int
    platform: str = "linkedin"
    linkedin_account_id: int | None = None
    social_account_id: int | None = None
    status: str
    linkedin_post_urn: str | None = None
    remote_post_id: str | None = None
    error_message: str | None = None
    attempt_count: int
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
