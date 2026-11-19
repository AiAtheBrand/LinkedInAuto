from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PostUpdate(BaseModel):
    content: str
    image_url: str | None = None


class PostResponse(BaseModel):
    id: int
    user_id: int
    learning_id: int
    content: str
    status: str
    image_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
