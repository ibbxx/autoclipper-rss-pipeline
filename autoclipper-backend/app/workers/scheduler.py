import time
from uuid import uuid4
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models import Channel, Video
from app.services.youtube import parse_feed
from app.workers.queue import queue
from app.workers.jobs import process_video_job

def init_db():
    """Create tables if they don't exist"""
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables ready.")

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

                queue.enqueue(process_video_job, v.id, job_timeout=3600)
    except Exception as e:
        print(f"Error in tick: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Wait for DB to be ready
    for attempt in range(10):
        try:
            init_db()
            break
        except Exception as e:
            print(f"DB not ready (attempt {attempt + 1}/10): {e}")
            time.sleep(3)
    
    print(f"Scheduler started. Polling every {settings.poll_interval_seconds}s")
    while True:
        tick()
        time.sleep(settings.poll_interval_seconds)

