from datetime import datetime
from pydantic import BaseModel

class VideoOut(BaseModel):
    id: str
    channel_id: str
    youtube_video_id: str
    title: str
    published_at: datetime
    status: str
    progress: int | None = None
    error_message: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True

