from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions in workers."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
