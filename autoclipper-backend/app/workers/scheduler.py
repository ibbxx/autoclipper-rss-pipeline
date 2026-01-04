"""
Scheduler - RSS Polling with Forward-Only Processing
Only processes videos uploaded AFTER the channel's baseline.
"""
import time
from uuid import uuid4
from datetime import datetime
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
    """
    Poll RSS feeds for all active channels.
    Only enqueue videos that are NEWER than the channel's baseline.
    """
    db: Session = SessionLocal()
    try:
        channels = db.query(Channel).filter(Channel.is_active == True).all()
        
        for ch in channels:
            try:
                entries = parse_feed(ch.youtube_feed_url)
                
                if not entries:
                    continue
                
                # === CASE 1: Baseline not set (first poll after add) ===
                if not ch.baseline_set:
                    # Set baseline to most recent video, do NOT process anything
                    latest = entries[0]
                    ch.baseline_set = True
                    ch.last_seen_video_id = latest.get("youtube_video_id")
                    ch.last_seen_published_at = latest.get("published_at")
                    db.commit()
                    print(f"[{ch.name}] Baseline set: {ch.last_seen_video_id}")
                    continue
                
                # === CASE 2: Baseline exists, check for NEW videos ===
                new_videos = []
                
                for entry in entries:
                    yt_id = entry.get("youtube_video_id")
                    published_at = entry.get("published_at")
                    
                    if not yt_id:
                        continue
                    
                    # Skip if this is the baseline video or older
                    if yt_id == ch.last_seen_video_id:
                        break  # RSS is sorted newest-first, stop here
                    
                    # Skip if published_at is older than baseline
                    if ch.last_seen_published_at and published_at:
                        if isinstance(published_at, str):
                            try:
                                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                            except:
                                pass
                        if isinstance(ch.last_seen_published_at, datetime) and isinstance(published_at, datetime):
                            if published_at <= ch.last_seen_published_at:
                                continue
                    
                    # Check idempotency - skip if already in DB
                    exists = db.query(Video).filter(Video.youtube_video_id == yt_id).first()
                    if exists:
                        continue
                    
                    new_videos.append(entry)
                
                # Process new videos (newest first)
                for entry in new_videos:
                    yt_id = entry["youtube_video_id"]
                    
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
                    
                    print(f"[{ch.name}] New video detected: {entry['title']}")
                    queue.enqueue(process_video_job, v.id, job_timeout=3600)
                
                # Update baseline to newest video
                if new_videos:
                    newest = new_videos[0]
                    ch.last_seen_video_id = newest["youtube_video_id"]
                    ch.last_seen_published_at = newest["published_at"]
                    db.commit()
                    
            except Exception as e:
                print(f"[{ch.name}] Error polling: {e}")
                continue
                
    except Exception as e:
        print(f"Error in tick: {e}")
    finally:
        db.close()


def backfill_channel(channel_id: str, count: int = 3):
    """
    Optional: Manually backfill last N videos for a channel.
    Call this explicitly, NOT automatically on add.
    
    Usage: backfill_channel("channel-uuid", count=3)
    """
    db: Session = SessionLocal()
    try:
        ch = db.query(Channel).filter(Channel.id == channel_id).first()
        if not ch:
            print(f"Channel not found: {channel_id}")
            return
        
        entries = parse_feed(ch.youtube_feed_url)
        processed = 0
        
        for entry in entries[:count]:
            yt_id = entry.get("youtube_video_id")
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
                progress=0,
            )
            db.add(v)
            db.commit()
            
            queue.enqueue(process_video_job, v.id, job_timeout=3600)
            processed += 1
            print(f"[backfill] Enqueued: {entry['title']}")
        
        print(f"[backfill] Completed. Processed {processed} videos.")
        
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
    
    print(f"Scheduler started (forward-only mode). Polling every {settings.poll_interval_seconds}s")
    while True:
        tick()
        time.sleep(settings.poll_interval_seconds)
