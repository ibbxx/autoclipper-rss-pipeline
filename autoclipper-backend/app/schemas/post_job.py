from datetime import datetime
from pydantic import BaseModel

class PostJobOut(BaseModel):
    id: str
    clip_id: str
    status: str
    mode: str
    error_message: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True

