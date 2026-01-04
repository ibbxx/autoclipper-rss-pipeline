"""
Queue Configuration - Multi-queue setup with retry support
Separates io/ai/render workloads for optimal scaling
"""
from redis import Redis
from rq import Queue, Retry
from app.core.settings import settings
from app.core.settings_v2 import refactor_settings

# Redis connection
redis_conn = Redis.from_url(settings.redis_url)

# Legacy default queue (backwards compat)
queue = Queue(settings.rq_queue_name, connection=redis_conn)

# =============================================================================
# Pipeline V2: Separated Queues
# =============================================================================

# IO Queue: yt-dlp probe, audio download, file ops
io_queue = Queue(refactor_settings.rq_queue_io, connection=redis_conn)

# AI Queue: Whisper transcription, LLM calls
ai_queue = Queue(refactor_settings.rq_queue_ai, connection=redis_conn)

# Render Queue: FFmpeg processing
render_queue = Queue(refactor_settings.rq_queue_render, connection=redis_conn)


# =============================================================================
# Retry Configuration
# =============================================================================

def get_retry_config(max_retries: int = 3) -> Retry:
    """
    Default retry configuration with exponential backoff.
    Intervals: 30s, 60s, 120s
    """
    return Retry(max=max_retries, interval=[30, 60, 120])


# Convenience retry configs
RETRY_DEFAULT = get_retry_config(3)
RETRY_LLM = get_retry_config(5)     # LLM calls may hit rate limits
RETRY_RENDER = get_retry_config(2)  # Render failures usually need manual fix


# =============================================================================
# Helper Functions
# =============================================================================

def enqueue_io(func, *args, job_timeout=600, **kwargs):
    """Enqueue job to IO queue with retry"""
    return io_queue.enqueue(
        func, *args, 
        job_timeout=job_timeout,
        retry=RETRY_DEFAULT,
        **kwargs
    )

def enqueue_ai(func, *args, job_timeout=3600, **kwargs):
    """Enqueue job to AI queue with retry"""
    return ai_queue.enqueue(
        func, *args,
        job_timeout=job_timeout,
        retry=RETRY_LLM,
        **kwargs
    )

def enqueue_render(func, *args, job_timeout=1800, **kwargs):
    """Enqueue job to Render queue with retry"""
    return render_queue.enqueue(
        func, *args,
        job_timeout=job_timeout,
        retry=RETRY_RENDER,
        **kwargs
    )
