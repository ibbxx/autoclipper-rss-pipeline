
import sys
import os

# Add local path to import app modules
sys.path.append(os.getcwd())

from app.db.context import get_db_session
from app.models import Video, Clip

with get_db_session() as db:
    videos = db.query(Video).order_by(Video.created_at.desc()).limit(5).all()
    print(f"{'ID':<36} | {'Status':<15} | {'Progress':<10} | {'Title'}")
    print("-" * 100)
    for v in videos:
        print(f"{v.id:<36} | {v.status:<15} | {v.progress:<10} | {v.title}")
        if v.error_message:
            print(f"  [ERROR] {v.error_message}")
            
    print("\nChecking Clips for the latest video:")
    if videos:
        latest = videos[0]
        clips = db.query(Clip).filter(Clip.video_id == latest.id).all()
        print(f"Found {len(clips)} clips for video {latest.id}")
        for c in clips:
            print(f"  - {c.id} | Status: {c.render_status} | {c.start_sec}-{c.end_sec}s")
