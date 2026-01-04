from enum import Enum

class VideoStatus(str, Enum):
    NEW = "NEW"
    DOWNLOADING = "DOWNLOADING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    ERROR = "ERROR"

class RenderStatus(str, Enum):
    PENDING = "PENDING"
    RENDERING = "RENDERING"
    READY = "READY"
    ERROR = "ERROR"

class PostStatus(str, Enum):
    QUEUED = "QUEUED"
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    POSTED = "POSTED"
    FAILED = "FAILED"

class PostMode(str, Enum):
    DRAFT = "DRAFT"
    DIRECT = "DIRECT"
