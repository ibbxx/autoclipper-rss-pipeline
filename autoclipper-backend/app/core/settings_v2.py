"""
Refactor Settings - New environment variables for segment-first pipeline
"""
from __future__ import annotations
import os
from dataclasses import dataclass

def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    return default if v is None or v.strip() == "" else int(v)

def _env_str(name: str, default: str) -> str:
    v = os.getenv(name)
    return default if v is None or v.strip() == "" else v

def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    return default if v is None or v.strip() == "" else float(v)

@dataclass(frozen=True)
class RefactorSettings:
    # Whisper Pass 1 (fast)
    whisper_pass1_model: str = _env_str("WHISPER_PASS1_MODEL", "tiny")
    whisper_pass1_beam: int = _env_int("WHISPER_PASS1_BEAM", 1)
    
    # Whisper Pass 2 (accurate)
    whisper_pass2_model: str = _env_str("WHISPER_PASS2_MODEL", "small")
    whisper_pass2_beam: int = _env_int("WHISPER_PASS2_BEAM", 3)
    
    # Candidate generation
    cand_min_sec: int = _env_int("CAND_MIN_SEC", 60)
    cand_max_sec: int = _env_int("CAND_MAX_SEC", 120)
    cand_shift_sec: int = _env_int("CAND_SHIFT_SEC", 15)
    cand_max_per_video: int = _env_int("CAND_MAX_PER_VIDEO", 400)
    
    # LLM
    llm_shortlist_max: int = _env_int("LLM_SHORTLIST_MAX", 25)
    llm_send_max_candidates: int = _env_int("LLM_SEND_MAX_CANDIDATES", 120)
    
    # Queues
    rq_queue_io: str = _env_str("RQ_QUEUE_IO", "io")
    rq_queue_ai: str = _env_str("RQ_QUEUE_AI", "ai")
    rq_queue_render: str = _env_str("RQ_QUEUE_RENDER", "render")
    
    # Preview render (fast)
    preview_width: int = _env_int("PREVIEW_WIDTH", 540)
    preview_height: int = _env_int("PREVIEW_HEIGHT", 960)
    preview_crf: int = _env_int("PREVIEW_CRF", 30)
    preview_preset: str = _env_str("PREVIEW_PRESET", "veryfast")
    
    # Final render (quality)
    final_width: int = _env_int("FINAL_WIDTH", 1080)
    final_height: int = _env_int("FINAL_HEIGHT", 1920)
    final_crf: int = _env_int("FINAL_CRF", 22)
    final_preset: str = _env_str("FINAL_PRESET", "medium")

refactor_settings = RefactorSettings()
