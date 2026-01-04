from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4

from app.db.session import get_db
from app.models import Channel
from app.schemas.channel import ChannelCreate, ChannelUpdate, ChannelOut, ChannelResolveRequest, ChannelResolveResponse
from app.services.youtube import channel_feed_url, get_channel_id

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.post("/resolve", response_model=ChannelResolveResponse)
def resolve_channel(body: ChannelResolveRequest):
    """
    Resolve a YouTube URL (video, handle, or custom URL) to a canonical Channel ID.
    """
    result = get_channel_id(body.url)
    return ChannelResolveResponse(**result)

@router.get("", response_model=list[ChannelOut])
def list_channels(db: Session = Depends(get_db)):
    return db.query(Channel).order_by(Channel.created_at.desc()).all()

@router.post("", response_model=ChannelOut)
def create_channel(body: ChannelCreate, db: Session = Depends(get_db)):
    from app.services.youtube import parse_feed
    from app.models import Video
    from app.workers.queue import queue
    from app.workers.jobs import process_video_job
    
    if body.min_clip_sec >= body.max_clip_sec:
        raise HTTPException(status_code=400, detail="min_clip_sec must be < max_clip_sec")

    # Check if channel already exists
    existing = db.query(Channel).filter(Channel.youtube_channel_id == body.youtube_channel_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Channel sudah ada dengan nama '{existing.name}'")

    feed_url = channel_feed_url(body.youtube_channel_id)
    
    # Fetch RSS once to get the most recent video
    baseline_video_id = None
    baseline_published_at = None
    latest_entry = None
    
    try:
        entries = parse_feed(feed_url)
        if entries:
            latest_entry = entries[0]
            baseline_video_id = latest_entry.get("youtube_video_id")
            baseline_published_at = latest_entry.get("published_at")
    except Exception as e:
        pass  # If RSS fails, channel is still created
    
    # Create channel
    ch = Channel(
        id=str(uuid4()),
        name=body.name,
        youtube_channel_id=body.youtube_channel_id,
        youtube_feed_url=feed_url,
        is_active=body.is_active,
        clips_per_video=body.clips_per_video,
        min_clip_sec=body.min_clip_sec,
        max_clip_sec=body.max_clip_sec,
        baseline_set=baseline_video_id is not None,
        last_seen_video_id=baseline_video_id,
        last_seen_published_at=baseline_published_at,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    
    # === PROCESS 1 LATEST VIDEO (OPTIONAL) ===
    # Hanya proses jika user centang checkbox "Proses 1 video terbaru"
    if body.process_latest and latest_entry and baseline_video_id:
        # Check if video already exists (idempotency)
        video_exists = db.query(Video).filter(Video.youtube_video_id == baseline_video_id).first()
        
        if not video_exists:
            v = Video(
                id=str(uuid4()),
                channel_id=ch.id,
                youtube_video_id=baseline_video_id,
                title=latest_entry.get("title", "Unknown"),
                published_at=baseline_published_at,
                status="NEW",
                progress=0,
            )
            db.add(v)
            db.commit()
            
            # Enqueue processing
            # Enqueue processing
            from app.workers.orchestrator import start_pipeline_v2
            start_pipeline_v2(v.id, baseline_video_id)
    
    return ch

@router.patch("/{channel_id}", response_model=ChannelOut)
def update_channel(channel_id: str, body: ChannelUpdate, db: Session = Depends(get_db)):
    ch = db.query(Channel).filter(Channel.id == channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    if body.name is not None:
        ch.name = body.name
    if body.youtube_channel_id is not None:
        ch.youtube_channel_id = body.youtube_channel_id
        ch.youtube_feed_url = channel_feed_url(body.youtube_channel_id)
    if body.is_active is not None:
        ch.is_active = body.is_active
    if body.clips_per_video is not None:
        ch.clips_per_video = body.clips_per_video
    if body.min_clip_sec is not None:
        ch.min_clip_sec = body.min_clip_sec
    if body.max_clip_sec is not None:
        ch.max_clip_sec = body.max_clip_sec

    if ch.min_clip_sec >= ch.max_clip_sec:
        raise HTTPException(status_code=400, detail="min_clip_sec must be < max_clip_sec")

    db.commit()
    db.refresh(ch)
    return ch

@router.delete("/{channel_id}")
def delete_channel(channel_id: str, db: Session = Depends(get_db)):
    from app.models import Video, Clip, PostJob
    
    ch = db.query(Channel).filter(Channel.id == channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Get all videos for this channel
    videos = db.query(Video).filter(Video.channel_id == channel_id).all()
    video_ids = [v.id for v in videos]
    
    if video_ids:
        # Get all clips for these videos
        clips = db.query(Clip).filter(Clip.video_id.in_(video_ids)).all()
        clip_ids = [c.id for c in clips]
        
        if clip_ids:
            # Delete all post_jobs for these clips
            db.query(PostJob).filter(PostJob.clip_id.in_(clip_ids)).delete(synchronize_session=False)
        
        # Delete all clips for these videos
        db.query(Clip).filter(Clip.video_id.in_(video_ids)).delete(synchronize_session=False)
        
        # Delete all videos for this channel
        db.query(Video).filter(Video.channel_id == channel_id).delete(synchronize_session=False)
    
    # Finally delete the channel
    db.delete(ch)
    db.commit()
    return {"ok": True, "deleted_videos": len(video_ids)}


@router.post("/{channel_id}/backfill")
def backfill_channel(
    channel_id: str,
    count: int = 3,
    db: Session = Depends(get_db)
):
    """
    Explicitly backfill last N videos for a channel.
    
    This is a MANUAL action - forward-only baseline is NOT affected.
    Only videos not already in DB will be processed.
    
    Args:
        channel_id: Channel UUID
        count: Number of recent videos to backfill (default 3, max 10)
    """
    from uuid import uuid4
    from datetime import datetime, timezone
    from app.models import Video
    from app.services.youtube import parse_feed
    from app.workers.queue import queue
    from app.workers.jobs import process_video_job
    
    # Safety limit
    MAX_BACKFILL = 10
    count = min(count, MAX_BACKFILL)
    
    if count < 1:
        raise HTTPException(status_code=400, detail="count must be at least 1")
    
    ch = db.query(Channel).filter(Channel.id == channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Optional: Rate limit backfill
    # Uncomment to prevent frequent backfill abuse
    # if ch.last_backfill_at:
    #     cooldown = datetime.now(timezone.utc) - ch.last_backfill_at
    #     if cooldown.total_seconds() < 3600:  # 1 hour cooldown
    #         raise HTTPException(status_code=429, detail="Backfill cooldown: wait 1 hour")
    
    # Fetch RSS
    try:
        entries = parse_feed(ch.youtube_feed_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch RSS: {e}")
    
    if not entries:
        return {"ok": True, "message": "No videos in RSS feed", "processed": 0}
    
    # Take top N entries
    entries_to_process = entries[:count]
    processed = 0
    skipped = 0
    
    for entry in entries_to_process:
        yt_id = entry.get("youtube_video_id")
        if not yt_id:
            continue
        
        # Idempotency: skip if already in DB
        exists = db.query(Video).filter(Video.youtube_video_id == yt_id).first()
        if exists:
            skipped += 1
            continue
        
        # Insert new video
        v = Video(
            id=str(uuid4()),
            channel_id=ch.id,
            youtube_video_id=yt_id,
            title=entry["title"],
            published_at=entry["published_at"],
            status="NEW",
            progress=0,
        )
        db.add(v)
        db.commit()
        
        # Enqueue processing
        # Enqueue processing
        from app.workers.orchestrator import start_pipeline_v2
        start_pipeline_v2(v.id, v.youtube_video_id)
        processed += 1
    
    return {
        "ok": True,
        "message": f"Backfill completed",
        "processed": processed,
        "skipped": skipped,
        "requested": count
    }
