from pydantic import BaseModel, Field

class ApproveVideoClipsIn(BaseModel):
    clip_ids: list[str] = Field(default_factory=list)
    mode: str = Field(default="DRAFT")
