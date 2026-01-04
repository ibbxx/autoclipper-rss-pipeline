
import sys
import os
from sqlalchemy import text

# Add local path to import app modules
sys.path.append(os.getcwd())

from app.db.context import get_db_session

def patch_schema():
    print("Patching database schema for max_clips_per_video...")
    with get_db_session() as db:
        try:
            db.execute(text("ALTER TABLE videos ADD COLUMN IF NOT EXISTS max_clips_per_video INTEGER;"))
            db.commit()
            print("Successfully added max_clips_per_video column.")
        except Exception as e:
            print(f"Error patching schema: {e}")
            db.rollback()

if __name__ == "__main__":
    patch_schema()
