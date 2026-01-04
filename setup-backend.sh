#!/usr/bin/env bash
set -euo pipefail

# =========================
# Auto Clipper Backend (FastAPI) - Full Scaffold
# =========================

APP_DIR="autoclipper-backend"

echo "==> 1) Create folder: $APP_DIR"
if [ -d "$APP_DIR" ]; then
  echo "Folder '$APP_DIR' already exists. Remove it or change APP_DIR."
  exit 1
fi
mkdir -p "$APP_DIR"
cd "$APP_DIR"

echo "==> 2) Create python project structure"
mkdir -p app/{api,core,db,models,schemas,services,workers}
mkdir -p app/api/routes
mkdir -p scripts

echo "==> 3) Write requirements.txt"
cat > requirements.txt <<'EOF'
fastapi==0.115.6
uvicorn[standard]==0.34.0
SQLAlchemy==2.0.36
psycopg2-binary==2.9.10
pydantic==2.10.4
pydantic-settings==2.7.1
python-dotenv==1.0.1
requests==2.32.3
feedparser==6.0.11
redis==5.2.1
rq==1.16.2
apscheduler==3.10.4
EOF

echo "==> 4) Create .env.example"
cat > .env.example <<'EOF'
# API
APP_ENV=dev
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Database
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/autoclipper

# Redis / Queue
REDIS_URL=redis://redis:6379/0
RQ_QUEUE_NAME=default

# Scheduler
POLL_INTERVAL_SECONDS=600
EOF

echo "==> 5) Docker compose (api + db + redis + worker)"
cat > docker-compose.yml <<'EOF'
services:
  api:
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    volumes:
      - ./:/app
    command: ["bash", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]

  worker:
    build: .
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - ./:/app
    command: ["bash", "-lc", "python -m app.workers.worker"]

  scheduler:
    build: .
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - ./:/app
    command: ["bash", "-lc", "python -m app.workers.scheduler"]

  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_USER: postgres
      POSTGRES_DB: autoclipper
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  pgdata:
EOF

echo "==> 6) Dockerfile"
cat > Dockerfile <<'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
EOF

echo "==> 7) Core settings"
cat > app/core/settings.py <<'EOF'
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    rq_queue_name: str = Field(default="default", alias="RQ_QUEUE_NAME")

    poll_interval_seconds: int = Field(default=600, alias="POLL_INTERVAL_SECONDS")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
EOF

echo "==> 8) DB session + base"
cat > app/db/base.py <<'EOF'
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
EOF

cat > app/db/session.py <<'EOF'
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.settings import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
EOF

echo "==> 9) Models"
cat > app/models/channel.py <<'EOF'
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

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
EOF

cat > app/models/video.py <<'EOF'
from sqlalchemy import String, DateTime, ForeignKey, func
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
    progress: Mapped[int] = mapped_column(String, default="0")
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
EOF

cat > app/models/clip.py <<'EOF'
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, func
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

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
EOF

cat > app/models/post_job.py <<'EOF'
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
EOF

cat > app/models/__init__.py <<'EOF'
from app.models.channel import Channel
from app.models.video import Video
from app.models.clip import Clip
from app.models.post_job import PostJob
EOF

echo "==> 10) Schemas"
cat > app/schemas/channel.py <<'EOF'
from pydantic import BaseModel, Field

class ChannelBase(BaseModel):
    name: str
    youtube_channel_id: str
    is_active: bool = True
    clips_per_video: int = Field(default=4, ge=1, le=10)
    min_clip_sec: int = Field(default=20, ge=5, le=120)
    max_clip_sec: int = Field(default=45, ge=6, le=180)

class ChannelCreate(ChannelBase):
    pass

class ChannelUpdate(BaseModel):
    name: str | None = None
    youtube_channel_id: str | None = None
    is_active: bool | None = None
    clips_per_video: int | None = Field(default=None, ge=1, le=10)
    min_clip_sec: int | None = Field(default=None, ge=5, le=120)
    max_clip_sec: int | None = Field(default=None, ge=6, le=180)

class ChannelOut(ChannelBase):
    id: str
    youtube_feed_url: str
    created_at: str

    class Config:
        from_attributes = True
EOF

cat > app/schemas/video.py <<'EOF'
from pydantic import BaseModel

class VideoOut(BaseModel):
    id: str
    channel_id: str
    youtube_video_id: str
    title: str
    published_at: str
    status: str
    progress: int | None = None
    error_message: str | None = None
    created_at: str

    class Config:
        from_attributes = True
EOF

cat > app/schemas/clip.py <<'EOF'
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
EOF

cat > app/schemas/post_job.py <<'EOF'
from pydantic import BaseModel

class PostJobOut(BaseModel):
    id: str
    clip_id: str
    status: str
    mode: str
    error_message: str | None = None
    created_at: str

    class Config:
        from_attributes = True
EOF

cat > app/schemas/actions.py <<'EOF'
from pydantic import BaseModel, Field

class ApproveVideoClipsIn(BaseModel):
    clip_ids: list[str] = Field(default_factory=list)
    mode: str = Field(default="DRAFT")
EOF

echo "==> 11) Services: YouTube RSS monitor"
cat > app/services/youtube.py <<'EOF'
import feedparser
from datetime import datetime, timezone
from typing import Iterable

def channel_feed_url(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

def parse_feed(feed_url: str) -> Iterable[dict]:
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        yield {
            "youtube_video_id": getattr(entry, "yt_videoid", None),
            "title": getattr(entry, "title", "Untitled"),
            "published_at": _parse_datetime(getattr(entry, "published", None)),
        }

def _parse_datetime(s: str | None) -> datetime:
    if not s:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)
EOF

echo "==> 12) Queue (Redis + RQ)"
cat > app/workers/queue.py <<'EOF'
from redis import Redis
from rq import Queue
from app.core.settings import settings

redis_conn = Redis.from_url(settings.redis_url)
queue = Queue(settings.rq_queue_name, connection=redis_conn)
EOF

echo "==> 13) Worker jobs (placeholders)"
cat > app/workers/jobs.py <<'EOF'
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import Video, Clip, PostJob
from uuid import uuid4

def process_video_job(video_id: str):
    """Placeholder: Create 4 fake clips"""
    db: Session = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return

        video.status = "PROCESSING"
        db.commit()

        db.query(Clip).filter(Clip.video_id == video_id).delete()
        db.commit()

        for i in range(4):
            c = Clip(
                id=str(uuid4()),
                video_id=video_id,
                start_sec=float(i * 30),
                end_sec=float(i * 30 + 30),
                score=float(90 - i * 2),
                render_status="READY",
                file_url=f"https://example.com/clips/{video_id}/{i}.mp4",
                thumb_url=f"https://example.com/clips/{video_id}/{i}.jpg",
                suggested_caption=f"Clip {i+1} (auto)",
                approved=False,
            )
            db.add(c)

        video.status = "READY"
        video.error_message = None
        db.commit()
    except Exception as e:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = "ERROR"
            video.error_message = str(e)
            db.commit()
    finally:
        db.close()

def upload_tiktok_job(post_job_id: str):
    """Placeholder: Mark job as POSTED"""
    db: Session = SessionLocal()
    try:
        job = db.query(PostJob).filter(PostJob.id == post_job_id).first()
        if not job:
            return
        job.status = "UPLOADING"
        db.commit()

        job.status = "POSTED"
        job.error_message = None
        db.commit()
    except Exception as e:
        job = db.query(PostJob).filter(PostJob.id == post_job_id).first()
        if job:
            job.status = "FAILED"
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()
EOF

echo "==> 14) Worker runner"
cat > app/workers/worker.py <<'EOF'
from rq import Worker
from app.workers.queue import queue, redis_conn

if __name__ == "__main__":
    w = Worker([queue], connection=redis_conn)
    w.work()
EOF

echo "==> 15) Scheduler"
cat > app/workers/scheduler.py <<'EOF'
import time
from uuid import uuid4
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.session import SessionLocal
from app.models import Channel, Video
from app.services.youtube import parse_feed
from app.workers.queue import queue
from app.workers.jobs import process_video_job

def tick():
    db: Session = SessionLocal()
    try:
        channels = db.query(Channel).filter(Channel.is_active == True).all()
        for ch in channels:
            for entry in parse_feed(ch.youtube_feed_url):
                yt_id = entry["youtube_video_id"]
                if not yt_id:
                    continue
                exists = db.query(Video).filter(Video.youtube_video_id == yt_id).first()
                if exists:
                    continue

                v = Video(
                    id=str(uuid4()),
                    channel_id=ch.id,
                    youtube_video_id=yt_id,
                    title=entry["title"],
                    published_at=entry["published_at"],
                    status="NEW",
                    progress="0",
                )
                db.add(v)
                db.commit()

                queue.enqueue(process_video_job, v.id)
    finally:
        db.close()

if __name__ == "__main__":
    while True:
        tick()
        time.sleep(settings.poll_interval_seconds)
EOF

echo "==> 16) API routes"
cat > app/api/routes/health.py <<'EOF'
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {"ok": True}
EOF

cat > app/api/routes/channels.py <<'EOF'
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4

from app.db.session import get_db
from app.models import Channel
from app.schemas.channel import ChannelCreate, ChannelUpdate, ChannelOut
from app.services.youtube import channel_feed_url

router = APIRouter(prefix="/api/channels", tags=["channels"])

@router.get("", response_model=list[ChannelOut])
def list_channels(db: Session = Depends(get_db)):
    return db.query(Channel).order_by(Channel.created_at.desc()).all()

@router.post("", response_model=ChannelOut)
def create_channel(body: ChannelCreate, db: Session = Depends(get_db)):
    if body.min_clip_sec >= body.max_clip_sec:
        raise HTTPException(status_code=400, detail="min_clip_sec must be < max_clip_sec")

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
    ch = db.query(Channel).filter(Channel.id == channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    db.delete(ch)
    db.commit()
    return {"ok": True}
EOF

cat > app/api/routes/videos.py <<'EOF'
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
EOF

echo "==> 17) API router + app main"
cat > app/api/router.py <<'EOF'
from fastapi import APIRouter
from app.api.routes.health import router as health
from app.api.routes.channels import router as channels
from app.api.routes.videos import router as videos

router = APIRouter()
router.include_router(health)
router.include_router(channels)
router.include_router(videos)
EOF

cat > app/main.py <<'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.api.router import router
from app.db.session import engine
from app.db.base import Base

app = FastAPI(title="Auto Clipper Backend", version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(router)
EOF

echo "==> 18) Make python module runnable"
cat > app/__init__.py <<'EOF'
# app package
EOF

echo "==> 19) Create .env from example"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env (edit it if needed)."
fi

echo ""
echo "✅ Backend scaffold created in: $APP_DIR"
echo ""
echo "Next steps:"
echo "1) Start services:"
echo "   docker compose up --build"
echo ""
echo "2) Test health:"
echo "   curl http://localhost:8000/health"
