from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LearningCreate(BaseModel):
    topic: str
    category: str
    problem: str | None = None
    what_i_learned: str
    project: str | None = None
    lesson: str | None = None


class LearningResponse(LearningCreate):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
