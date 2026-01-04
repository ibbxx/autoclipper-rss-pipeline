from enum import Enum

class VideoStatus(str, Enum):
    # Initial state
    NEW = "NEW"
    
    # Pipeline V2 states (ordered)
    PROBING = "PROBING"
    GENERATING_CANDIDATES = "GENERATING_CANDIDATES"
    TRANSCRIBING_PASS1 = "TRANSCRIBING_PASS1"
    LLM_SHORTLISTING = "LLM_SHORTLISTING"
    TRANSCRIBING_PASS2 = "TRANSCRIBING_PASS2"
    LLM_REFINING = "LLM_REFINING"
    RENDERING_PREVIEW = "RENDERING_PREVIEW"
    
    # Legacy states (keep for backwards compat)
    DOWNLOADING = "DOWNLOADING"
    PROCESSING = "PROCESSING"
    
    # Terminal states
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
