from sqlalchemy import String, Boolean, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    youtube_channel_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    youtube_feed_url: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    clips_per_video: Mapped[int] = mapped_column(Integer, default=4)
    min_clip_sec: Mapped[int] = mapped_column(Integer, default=20)
    max_clip_sec: Mapped[int] = mapped_column(Integer, default=45)

    # Forward-only baseline tracking
    baseline_set: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_video_id: Mapped[str | None] = mapped_column(String, nullable=True)
    last_seen_published_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

