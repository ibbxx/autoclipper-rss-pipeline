
import sys
import os
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import text

# Add local path to import app modules
sys.path.append(os.getcwd())

from app.db.context import get_db_session
from app.models import Channel, Video
from app.workers.orchestrator import start_pipeline_v2

VIDEO_URL = "https://youtu.be/aSxLg7fRuFs?si=UwrgZbjcSJnvll1G"
YOUTUBE_ID = "aSxLg7fRuFs" # Extracted from URL manually for safety

def manual_trigger():
    print(f"--- MANUAL TRIGGER START ---")
    print(f"Target Video: {VIDEO_URL}")
    
    with get_db_session() as db:
        # 1. DELETE Manual Channel (Cascades to old videos)
        print("1. Cleaning up old 'Manual Videos' channel...")
        try:
            # We explicitly delete videos first to be safe, though cascade might handle it
            db.execute(text("DELETE FROM clips WHERE video_id IN (SELECT id FROM videos WHERE channel_id IN (SELECT id FROM channels WHERE youtube_channel_id = '__MANUAL__'))"))
            db.execute(text("DELETE FROM videos WHERE channel_id IN (SELECT id FROM channels WHERE youtube_channel_id = '__MANUAL__')"))
            db.execute(text("DELETE FROM channels WHERE youtube_channel_id = '__MANUAL__'"))
            db.commit()
            print("   Cleaned up old data.")
        except Exception as e:
            print(f"   Error cleaning up (might not exist): {e}")
            db.rollback()

        # 2. CREATE Manual Channel
        print("2. Re-creating 'Manual Videos' channel...")
        channel_id = str(uuid4())
        manual_channel = Channel(
            id=channel_id,
            name="Manual Videos",
            youtube_channel_id="__MANUAL__",
            youtube_feed_url="",
            is_active=False,
            baseline_set=True,
            min_clip_sec=75,
            max_clip_sec=180,
            clips_per_video=4
        )
        db.add(manual_channel)
        db.commit()
        print(f"   Created channel {channel_id}")

        # 3. CREATE Video
        print("3. Creating Video record...")
        video_id = str(uuid4())
        v = Video(
            id=video_id,
            channel_id=channel_id,
            youtube_video_id=YOUTUBE_ID,
            title="Manual Trigger Video",
            published_at=datetime.now(timezone.utc),
            status="NEW",
            progress=0,
            source="MANUAL",
            min_clip_duration=75,
            max_clip_duration=180,
            max_clips_per_video=4
        )
        db.add(v)
        db.commit()
        print(f"   Created video {video_id} (ID: {YOUTUBE_ID})")

        # 4. TRIGGER Pipeline
        print("4. Triggering Pipeline V2...")
        # We need to run this outside the session context usually, but start_pipeline_v2 handles its own queueing
        try:
            start_pipeline_v2(video_id, YOUTUBE_ID)
            print("   Pipeline triggered successfully!")
        except Exception as e:
             print(f"   Failed to trigger pipeline: {e}")

if __name__ == "__main__":
    manual_trigger()
