from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import re

from app.db.session import get_db
from app.models import Video, Clip, PostJob
from app.schemas.video import VideoOut
from app.schemas.clip import ClipOut, ClipUpdate
from app.schemas.actions import ApproveVideoClipsIn
from app.schemas.post_job import PostJobOut
from app.workers.queue import queue
# from app.workers.jobs import process_video_job, upload_tiktok_job
from uuid import uuid4
from datetime import datetime, timezone

router = APIRouter(prefix="/api", tags=["videos"])


class VideoCreate(BaseModel):
    """Request body for manual video add"""
    video_url: str
    min_clip_sec: int | None = None
    max_clip_sec: int | None = None
    max_clips_per_video: int | None = 4  # Default manual


def extract_youtube_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


@router.post("/videos", response_model=VideoOut)
def create_video(body: VideoCreate, db: Session = Depends(get_db)):
    """
    Add Video - Manual proses 1 video dari URL.
    
    Terpisah dari Add Channel, tidak bergantung RSS.
    Video akan langsung diproses pipeline.
    """
    # Extract video ID
    yt_id = extract_youtube_video_id(body.video_url)
    if not yt_id:
        raise HTTPException(status_code=400, detail="URL tidak valid. Gunakan format YouTube URL.")
    
    # Check if video already exists
    existing = db.query(Video).filter(Video.youtube_video_id == yt_id).first()
    if existing:
        # If ERROR, allow retry
        if existing.status == "ERROR":
            existing.status = "NEW"
            existing.progress = 0
            existing.error_message = None
            db.commit()
            
            # Restart pipeline
            from app.workers.orchestrator import start_pipeline_v2
            start_pipeline_v2(existing.id, existing.youtube_video_id)
            return existing
            
        # Return existing video info
        return existing
    
    # Get video info via yt-dlp probe (optional enhancement)
    title = f"Manual Video {yt_id}"
    published_at = datetime.now(timezone.utc)
    channel_id = None
    
    try:
        from app.services.ytdlp_probe import probe_video_metadata
        meta = probe_video_metadata(f"https://www.youtube.com/watch?v={yt_id}")
        title = meta.title or title
        # Note: For manual videos, we may not have a channel in our DB
    except Exception:
        pass
    
    # For manual videos, we need a channel_id
    # Option 1: Create a special "Manual" channel
    # Option 2: Require channel_id in request
    # For simplicity, we'll create/get a special manual channel
    from app.models import Channel
    manual_channel = db.query(Channel).filter(Channel.youtube_channel_id == "__MANUAL__").first()
    if not manual_channel:
        manual_channel = Channel(
            id=str(uuid4()),
            name="Manual Videos",
            youtube_channel_id="__MANUAL__",
            youtube_feed_url="",
            is_active=False,  # Don't poll RSS for this channel
            baseline_set=True,
        )
        db.add(manual_channel)
        db.commit()
    
    channel_id = manual_channel.id
    
    # Create video record
    v = Video(
        id=str(uuid4()),
        channel_id=channel_id,
        youtube_video_id=yt_id,
        title=title,
        published_at=published_at,
        status="NEW",
        progress=0,
        source="MANUAL",
        # Store clip duration constraints if provided
        min_clip_duration=body.min_clip_sec,
        max_clip_duration=body.max_clip_sec,
        max_clips_per_video=body.max_clips_per_video,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    
    # Enqueue processing
    # Start Pipeline V2
    from app.workers.orchestrator import start_pipeline_v2
    start_pipeline_v2(v.id, v.youtube_video_id)
    
    return v

@router.get("/videos", response_model=list[VideoOut])
def list_videos(
    status: str | None = Query(default=None),
    channel_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Video)
    if status:
        q = q.filter(Video.status == status)
    if channel_id:
        q = q.filter(Video.channel_id == channel_id)
    return q.order_by(Video.published_at.desc()).all()

@router.get("/videos/{video_id}", response_model=VideoOut)
def get_video(video_id: str, db: Session = Depends(get_db)):
    v = db.query(Video).filter(Video.id == video_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    return v

@router.get("/videos/{video_id}/clips", response_model=list[ClipOut])
def list_clips(video_id: str, db: Session = Depends(get_db)):
    return db.query(Clip).filter(Clip.video_id == video_id).order_by(Clip.score.desc()).all()

@router.patch("/clips/{clip_id}", response_model=ClipOut)
def update_clip(clip_id: str, body: ClipUpdate, db: Session = Depends(get_db)):
    c = db.query(Clip).filter(Clip.id == clip_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")
    if body.approved is not None:
        c.approved = body.approved
    if body.suggested_caption is not None:
        c.suggested_caption = body.suggested_caption
    db.commit()
    db.refresh(c)
    return c

@router.post("/videos/{video_id}/approve")
def approve_and_upload(video_id: str, body: ApproveVideoClipsIn, db: Session = Depends(get_db)):
    clips = db.query(Clip).filter(Clip.video_id == video_id, Clip.id.in_(body.clip_ids)).all()
    if len(clips) != len(body.clip_ids):
        raise HTTPException(status_code=400, detail="Some clips not found for this video")

    for c in clips:
        if c.render_status != "READY":
            raise HTTPException(status_code=400, detail=f"Clip {c.id} not READY")
        c.approved = True

    db.commit()

    created_jobs = []
    for c in clips:
        job = PostJob(
            id=str(uuid4()),
            clip_id=c.id,
            status="QUEUED",
            mode=body.mode,
        )
        db.add(job)
        created_jobs.append(job)

    db.commit()

    # for j in created_jobs:
    #     queue.enqueue(upload_tiktok_job, j.id)
    # TODO: Re-implement upload_tiktok_job in pipeline v2

    return {"ok": True, "jobs_created": len(created_jobs)}

@router.get("/posts", response_model=list[PostJobOut])
def list_posts(status: str | None = Query(default=None), db: Session = Depends(get_db)):
    q = db.query(PostJob)
    if status:
        q = q.filter(PostJob.status == status)
    return q.order_by(PostJob.created_at.desc()).all()
