"""
Pipeline Orchestrator - State machine + job chaining with DB persistence
Manages video status transitions and enqueues next jobs in pipeline.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import uuid4

from app.db.session import SessionLocal
from app.models import Video, Clip
from app.core.enums import VideoStatus
from app.workers.queue import enqueue_io, enqueue_ai, enqueue_render
from app.workers.pipeline_v2 import (
    probe_metadata_job,
    generate_candidates_job,
    transcribe_pass1_job,
    llm_shortlist_job,
    transcribe_pass2_job,
    llm_refine_job,
)

logger = logging.getLogger(__name__)


def update_video_status(video_id: str, status: VideoStatus, error_message: Optional[str] = None):
    """Update video status in database."""
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = status.value
            if error_message:
                video.error_message = error_message
            db.commit()
            logger.info(f"[orchestrator] Video {video_id} -> {status.value}")
    finally:
        db.close()


def save_video_metadata(video_id: str, duration_sec: float, chapters_json: list, strategy: str):
    """Save probe metadata to video record."""
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.duration_sec = duration_sec
            video.chapters_json = chapters_json
            video.strategy = strategy
            db.commit()
    finally:
        db.close()


def save_candidates_to_db(video_id: str, candidates: list):
    """Save candidates as Clip records with status CANDIDATE."""
    db = SessionLocal()
    try:
        for cand in candidates:
            clip = Clip(
                id=cand["id"],
                video_id=video_id,
                start_sec=cand["start_sec"],
                end_sec=cand["end_sec"],
                source_strategy=cand.get("strategy"),
                render_status="CANDIDATE",
            )
            db.add(clip)
        db.commit()
        logger.info(f"[orchestrator] Saved {len(candidates)} candidates for video {video_id}")
    finally:
        db.close()


# =============================================================================
# Orchestrated Pipeline Jobs (with state machine)
# =============================================================================

def start_pipeline_v2(video_id: str, youtube_video_id: str):
    """
    Entry point: Start the V2 pipeline for a video.
    Called by scheduler when new video is detected.
    """
    logger.info(f"[orchestrator] Starting pipeline V2 for video: {video_id}")
    update_video_status(video_id, VideoStatus.PROBING)
    enqueue_io(orchestrated_probe_metadata, video_id, youtube_video_id)


def orchestrated_probe_metadata(video_id: str, youtube_video_id: str):
    """Step 1: Probe metadata, then enqueue Step 2."""
    try:
        result = probe_metadata_job(video_id, youtube_video_id)
        
        # Persist metadata
        save_video_metadata(
            video_id=video_id,
            duration_sec=result["duration_sec"],
            chapters_json=result["chapters"],
            strategy=result["strategy"]
        )
        
        # Transition state
        update_video_status(video_id, VideoStatus.GENERATING_CANDIDATES)
        
        # Enqueue next step
        enqueue_io(
            orchestrated_generate_candidates,
            video_id,
            youtube_video_id,
            result["duration_sec"],
            result["chapters"]
        )
        
    except Exception as e:
        logger.error(f"[orchestrator] probe_metadata failed: {e}")
        update_video_status(video_id, VideoStatus.ERROR, str(e))
        raise


def orchestrated_generate_candidates(
    video_id: str,
    youtube_video_id: str,
    duration_sec: float,
    chapters: list
):
    """Step 2: Generate candidates, then enqueue Step 3."""
    try:
        # Fetch video to check for duration constraints
        db = SessionLocal()
        min_dur = None
        max_dur = None
        max_items = None
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                min_dur = video.min_clip_duration
                max_dur = video.max_clip_duration
                max_items = video.max_clips_per_video
        finally:
            db.close()

        candidates = generate_candidates_job(
            video_id, 
            youtube_video_id, 
            duration_sec, 
            chapters,
            min_dur=min_dur,
            max_dur=max_dur,
            max_items=max_items
        )
        
        # Persist candidates
        save_candidates_to_db(video_id, candidates)
        
        # Transition state
        update_video_status(video_id, VideoStatus.TRANSCRIBING_PASS1)
        
        # Enqueue next step
        enqueue_ai(
            orchestrated_transcribe_pass1,
            video_id,
            youtube_video_id,
            candidates
        )
        
    except Exception as e:
        logger.error(f"[orchestrator] generate_candidates failed: {e}")
        update_video_status(video_id, VideoStatus.ERROR, str(e))
        raise


def orchestrated_transcribe_pass1(
    video_id: str,
    youtube_video_id: str,
    candidates: list
):
    """Step 3: Fast transcription, then enqueue Step 4."""
    try:
        transcribed = transcribe_pass1_job(video_id, youtube_video_id, candidates)
        
        # Update clips with transcript_pass1
        db = SessionLocal()
        try:
            for cand in transcribed:
                clip = db.query(Clip).filter(Clip.id == cand["id"]).first()
                if clip:
                    clip.transcript_pass1 = cand.get("transcript_pass1", "")
            db.commit()
        finally:
            db.close()
        
        # Transition state
        update_video_status(video_id, VideoStatus.LLM_SHORTLISTING)
        
        # Enqueue next step
        enqueue_ai(
            orchestrated_llm_shortlist,
            video_id,
            youtube_video_id,
            transcribed
        )
        
    except Exception as e:
        logger.error(f"[orchestrator] transcribe_pass1 failed: {e}")
        update_video_status(video_id, VideoStatus.ERROR, str(e))
        raise


def orchestrated_llm_shortlist(
    video_id: str,
    youtube_video_id: str,
    candidates: list
):
    """Step 4: LLM shortlist, then enqueue Step 5."""
    try:
        shortlisted = llm_shortlist_job(video_id, candidates)
        
        # Update clips with LLM results
        db = SessionLocal()
        try:
            for clip_data in shortlisted:
                # Find or create clip
                clip = db.query(Clip).filter(
                    Clip.video_id == video_id,
                    Clip.start_sec >= clip_data["start_sec"] - 2,
                    Clip.start_sec <= clip_data["start_sec"] + 2
                ).first()
                
                if clip:
                    clip.llm_viral_score = clip_data.get("viral_score")
                    clip.hook_text = clip_data.get("hook_text")
                    clip.suggested_caption = clip_data.get("caption")
                    clip.risk_flags = clip_data.get("risk_flags")
                    clip.keywords = clip_data.get("keywords")
                    clip.features_json = clip_data.get("features_json")
                    clip.final_score = clip_data.get("final_score")
                    clip.render_status = "SHORTLISTED"
            db.commit()
        finally:
            db.close()
        
        # Transition state
        update_video_status(video_id, VideoStatus.TRANSCRIBING_PASS2)
        
        # Enqueue next step
        enqueue_ai(
            orchestrated_transcribe_pass2,
            video_id,
            youtube_video_id,
            shortlisted
        )
        
    except Exception as e:
        logger.error(f"[orchestrator] llm_shortlist failed: {e}")
        update_video_status(video_id, VideoStatus.ERROR, str(e))
        raise


def orchestrated_transcribe_pass2(
    video_id: str,
    youtube_video_id: str,
    clips: list
):
    """Step 5: Accurate transcription, then enqueue Step 6."""
    try:
        transcribed = transcribe_pass2_job(video_id, youtube_video_id, clips)
        
        # Update clips with pass2 transcript
        db = SessionLocal()
        try:
            for clip_data in transcribed:
                clip = db.query(Clip).filter(
                    Clip.video_id == video_id,
                    Clip.start_sec >= clip_data["start_sec"] - 2,
                    Clip.start_sec <= clip_data["start_sec"] + 2
                ).first()
                
                if clip:
                    clip.transcript_pass2 = clip_data.get("transcript_pass2")
                    clip.word_timing_json = clip_data.get("word_timing")
            db.commit()
        finally:
            db.close()
        
        # Transition state
        update_video_status(video_id, VideoStatus.LLM_REFINING)
        
        # Enqueue next step
        enqueue_ai(orchestrated_llm_refine, video_id, transcribed)
        
    except Exception as e:
        logger.error(f"[orchestrator] transcribe_pass2 failed: {e}")
        update_video_status(video_id, VideoStatus.ERROR, str(e))
        raise


def orchestrated_llm_refine(video_id: str, clips: list):
    """Step 6: LLM refine, then mark READY for preview."""
    try:
        refined = llm_refine_job(clips)
        
        # Update clips with refined data
        db = SessionLocal()
        try:
            for clip_data in refined:
                clip = db.query(Clip).filter(
                    Clip.video_id == video_id,
                    Clip.start_sec >= clip_data["start_sec"] - 2,
                    Clip.start_sec <= clip_data["start_sec"] + 2
                ).first()
                
                if clip:
                    clip.hook_text = clip_data.get("hook_text")
                    clip.suggested_caption = clip_data.get("caption")
                    clip.risk_flags = clip_data.get("risk_flags")
                    clip.keywords = clip_data.get("keywords")
                    clip.render_status = "READY"
            db.commit()
        finally:
            db.close()
        
        # Transition to READY
        update_video_status(video_id, VideoStatus.READY)
        
        logger.info(f"[orchestrator] Pipeline V2 completed for video: {video_id}")
        
    except Exception as e:
        logger.error(f"[orchestrator] llm_refine failed: {e}")
        update_video_status(video_id, VideoStatus.ERROR, str(e))
        raise
