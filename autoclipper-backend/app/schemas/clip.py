from pydantic import BaseModel

class ClipOut(BaseModel):
    id: str
    video_id: str
    start_sec: float
    end_sec: float
    score: float
    file_url: str
    thumb_url: str
    subtitle_srt_url: str | None = None
    suggested_caption: str | None = None
    approved: bool
    render_status: str

    class Config:
        from_attributes = True

class ClipUpdate(BaseModel):
    approved: bool | None = None
    suggested_caption: str | None = None
