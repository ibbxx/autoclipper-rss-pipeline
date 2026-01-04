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
    if body.min_clip_sec >= body.max_clip_sec:
        raise HTTPException(status_code=400, detail="min_clip_sec must be < max_clip_sec")

    # Check if channel already exists
    existing = db.query(Channel).filter(Channel.youtube_channel_id == body.youtube_channel_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Channel sudah ada dengan nama '{existing.name}'")

    feed_url = channel_feed_url(body.youtube_channel_id)
    ch = Channel(
        id=str(uuid4()),
        name=body.name,
        youtube_channel_id=body.youtube_channel_id,
        youtube_feed_url=feed_url,
        is_active=body.is_active,
        clips_per_video=body.clips_per_video,
        min_clip_sec=body.min_clip_sec,
        max_clip_sec=body.max_clip_sec,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
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

