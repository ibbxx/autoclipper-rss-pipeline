from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class PostJob(Base):
    __tablename__ = "post_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    clip_id: Mapped[str] = mapped_column(String, ForeignKey("clips.id"), nullable=False)

    mode: Mapped[str] = mapped_column(String, default="DRAFT")
    status: Mapped[str] = mapped_column(String, default="QUEUED")

    tiktok_publish_id: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
