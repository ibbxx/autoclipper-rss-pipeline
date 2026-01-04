"""
Logging Configuration - Structured logging with job context
"""
import logging
import json
import sys
from datetime import datetime
from typing import Optional
from contextvars import ContextVar

# Context variables for job tracking
current_job_id: ContextVar[Optional[str]] = ContextVar('current_job_id', default=None)
current_video_id: ContextVar[Optional[str]] = ContextVar('current_video_id', default=None)


class StructuredFormatter(logging.Formatter):
    """
    JSON-structured log formatter with job context.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add job context if available
        job_id = current_job_id.get()
        video_id = current_video_id.get()
        
        if job_id:
            log_data["job_id"] = job_id
        if video_id:
            log_data["video_id"] = video_id
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
            
        return json.dumps(log_data)


def setup_logging(level: str = "INFO", structured: bool = True):
    """
    Configure application logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        structured: Use JSON format (True) or human-readable (False)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))
    
    if structured:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        ))
    
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


class JobContext:
    """
    Context manager for setting job context in logs.
    
    Usage:
        with JobContext(job_id="abc123", video_id="xyz"):
            logger.info("Processing...")  # Will include job_id and video_id
    """
    def __init__(self, job_id: Optional[str] = None, video_id: Optional[str] = None):
        self.job_id = job_id
        self.video_id = video_id
        self._tokens = []
        
    def __enter__(self):
        if self.job_id:
            self._tokens.append(current_job_id.set(self.job_id))
        if self.video_id:
            self._tokens.append(current_video_id.set(self.video_id))
        return self
        
    def __exit__(self, *args):
        for token in self._tokens:
            # Reset to previous value
            pass


# Initialize logging on import
setup_logging(level="INFO", structured=False)  # Use human-readable for dev
