from datetime import datetime
from pydantic import BaseModel, Field

class ChannelBase(BaseModel):
    name: str
    youtube_channel_id: str
    is_active: bool = True
    clips_per_video: int = Field(default=4, ge=1, le=10)
    min_clip_sec: int = Field(default=20, ge=5, le=120)
    max_clip_sec: int = Field(default=45, ge=6, le=180)

class ChannelCreate(ChannelBase):
    process_latest: bool = False  # Proses 1 video terbaru saat add channel
    clips_per_video: int = 4
    min_clip_sec: int = 75  # Default baru untuk edukasi
    max_clip_sec: int = 180

class ChannelUpdate(BaseModel):
    name: str | None = None
    youtube_channel_id: str | None = None
    is_active: bool | None = None
    clips_per_video: int | None = Field(default=None, ge=1, le=10)
    min_clip_sec: int | None = Field(default=None, ge=5, le=120)
    max_clip_sec: int | None = Field(default=None, ge=6, le=180)

class ChannelOut(ChannelBase):
    id: str
    youtube_feed_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChannelResolveRequest(BaseModel):
    url: str = Field(..., description="YouTube URL or handle to resolve")


class ChannelResolveResponse(BaseModel):
    channel_id: str | None = None
    name: str | None = None
    error: str | None = None
