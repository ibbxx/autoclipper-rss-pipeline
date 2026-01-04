from typing import TypeVar, Generic, Type, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from app.db.base import Base

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    """Generic repository for CRUD operations."""
    
    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model
    
    def get_by_id(self, id: str) -> Optional[T]:
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self) -> list[T]:
        return self.db.query(self.model).all()
    
    def create(self, **kwargs) -> T:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid4())
        instance = self.model(**kwargs)
        self.db.add(instance)
        return instance
    
    def delete(self, id: str) -> bool:
        instance = self.get_by_id(id)
        if instance:
            self.db.delete(instance)
            return True
        return False


class VideoRepository(BaseRepository):
    """Repository for Video operations."""
    
    def __init__(self, db: Session):
        from app.models import Video
        super().__init__(db, Video)
    
    def get_by_youtube_id(self, youtube_video_id: str):
        return self.db.query(self.model).filter(
            self.model.youtube_video_id == youtube_video_id
        ).first()
    
    def get_by_status(self, status: str):
        return self.db.query(self.model).filter(
            self.model.status == status
        ).order_by(self.model.published_at.desc()).all()
    
    def get_by_channel(self, channel_id: str):
        return self.db.query(self.model).filter(
            self.model.channel_id == channel_id
        ).order_by(self.model.published_at.desc()).all()


class ClipRepository(BaseRepository):
    """Repository for Clip operations."""
    
    def __init__(self, db: Session):
        from app.models import Clip
        super().__init__(db, Clip)
    
    def get_by_video(self, video_id: str):
        return self.db.query(self.model).filter(
            self.model.video_id == video_id
        ).order_by(self.model.score.desc()).all()
    
    def delete_by_video(self, video_id: str) -> int:
        count = self.db.query(self.model).filter(
            self.model.video_id == video_id
        ).delete()
        return count
    
    def get_ready_clips(self, video_id: str):
        return self.db.query(self.model).filter(
            self.model.video_id == video_id,
            self.model.render_status == "READY"
        ).all()


class ChannelRepository(BaseRepository):
    """Repository for Channel operations."""
    
    def __init__(self, db: Session):
        from app.models import Channel
        super().__init__(db, Channel)
    
    def get_active(self):
        return self.db.query(self.model).filter(
            self.model.is_active == True
        ).all()
    
    def get_by_youtube_id(self, youtube_channel_id: str):
        return self.db.query(self.model).filter(
            self.model.youtube_channel_id == youtube_channel_id
        ).first()


class PostJobRepository(BaseRepository):
    """Repository for PostJob operations."""
    
    def __init__(self, db: Session):
        from app.models import PostJob
        super().__init__(db, PostJob)
    
    def get_by_status(self, status: str):
        return self.db.query(self.model).filter(
            self.model.status == status
        ).order_by(self.model.created_at.desc()).all()
    
    def get_by_clip(self, clip_id: str):
        return self.db.query(self.model).filter(
            self.model.clip_id == clip_id
        ).all()
