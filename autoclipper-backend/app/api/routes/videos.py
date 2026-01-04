from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Video, Clip, PostJob
from app.schemas.video import VideoOut
from app.schemas.clip import ClipOut, ClipUpdate
from app.schemas.actions import ApproveVideoClipsIn
from app.schemas.post_job import PostJobOut
from app.workers.queue import queue
from app.workers.jobs import upload_tiktok_job
from uuid import uuid4

router = APIRouter(prefix="/api", tags=["videos"])

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

    for j in created_jobs:
        queue.enqueue(upload_tiktok_job, j.id)

    return {"ok": True, "jobs_created": len(created_jobs)}

@router.get("/posts", response_model=list[PostJobOut])
def list_posts(status: str | None = Query(default=None), db: Session = Depends(get_db)):
    q = db.query(PostJob)
    if status:
        q = q.filter(PostJob.status == status)
    return q.order_by(PostJob.created_at.desc()).all()
