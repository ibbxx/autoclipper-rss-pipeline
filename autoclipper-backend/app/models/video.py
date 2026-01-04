from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Video(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    channel_id: Mapped[str] = mapped_column(String, ForeignKey("channels.id"), nullable=False)

    youtube_video_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    published_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[str] = mapped_column(String, default="NEW")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # Source: RSS (from channel polling) or MANUAL (from Add Video)
    source: Mapped[str] = mapped_column(String(20), default="RSS")

    # Pipeline V2: Metadata from yt-dlp probe
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    chapters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    strategy: Mapped[str | None] = mapped_column(String(20), nullable=True)  # CHAPTER or SILENCE

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


