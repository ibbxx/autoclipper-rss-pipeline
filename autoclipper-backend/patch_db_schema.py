
import sys
import os
from sqlalchemy import text

# Add local path to import app modules
sys.path.append(os.getcwd())

from app.db.context import get_db_session

def patch_schema():
    print("Patching database schema...")
    with get_db_session() as db:
        try:
            # Check if column exists, if not add it
            # This is a bit rough, but effective for dev
            db.execute(text("ALTER TABLE videos ADD COLUMN IF NOT EXISTS min_clip_duration INTEGER;"))
            db.execute(text("ALTER TABLE videos ADD COLUMN IF NOT EXISTS max_clip_duration INTEGER;"))
            db.commit()
            print("Successfully added min_clip_duration and max_clip_duration columns.")
        except Exception as e:
            print(f"Error patching schema: {e}")
            db.rollback()

if __name__ == "__main__":
    patch_schema()
