
import sys
import os
from sqlalchemy import text

# Add local path to import app modules
sys.path.append(os.getcwd())

from app.db.context import get_db_session

def patch_manual_channel():
    print("Patching Manual Channel defaults...")
    with get_db_session() as db:
        try:
            # Update Manual Videos channel defaults
            db.execute(text("""
                UPDATE channels 
                SET min_clip_sec = 75, max_clip_sec = 180 
                WHERE youtube_channel_id = '__MANUAL__';
            """))
            db.commit()
            print("Successfully updated Manual Videos channel defaults.")
        except Exception as e:
            print(f"Error patching manual channel: {e}")
            db.rollback()

if __name__ == "__main__":
    patch_manual_channel()
