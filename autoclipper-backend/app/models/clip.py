from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, func, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    video_id: Mapped[str] = mapped_column(String, ForeignKey("videos.id"), nullable=False)

    start_sec: Mapped[float] = mapped_column(Float, nullable=False)
    end_sec: Mapped[float] = mapped_column(Float, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0)

    render_status: Mapped[str] = mapped_column(String, default="PENDING")

    file_url: Mapped[str] = mapped_column(String, default="")
    thumb_url: Mapped[str] = mapped_column(String, default="")
    subtitle_srt_url: Mapped[str | None] = mapped_column(String, nullable=True)

    suggested_caption: Mapped[str | None] = mapped_column(String, nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)

    # Pipeline V2: Two-pass transcription
    transcript_pass1: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_pass2: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_timing_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Pipeline V2: LLM scoring
    llm_viral_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    hook_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    risk_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    keywords: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    features_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Pipeline V2: Strategy info
    source_strategy: Mapped[str | None] = mapped_column(String(20), nullable=True)  # CHAPTER or SILENCE

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

