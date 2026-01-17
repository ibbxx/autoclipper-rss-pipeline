"""
Pipeline V2 - Segment-First Processing Jobs
New job functions for the refactored pipeline.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.settings_v2 import refactor_settings as settings
from app.services.ytdlp_probe import probe_video_metadata, download_audio_only
from app.services.candidate_segments import generate_candidates, Candidate
from app.services.scoring import compute_final_score, diversity_filter
from app.services.groq_prompts import format_shortlist_prompt, format_refine_prompt

logger = logging.getLogger(__name__)


# =============================================================================
# Job 1: Probe Metadata
# =============================================================================

def probe_metadata_job(video_id: str, youtube_video_id: str) -> Dict[str, Any]:
    """
    Probe video metadata via yt-dlp (duration, chapters).
    Does NOT download the video.
    
    Next job: generate_candidates_job
    Queue: io
    """
    logger.info(f"[probe_metadata] Starting for video: {video_id}")
    
    url = f"https://www.youtube.com/watch?v={youtube_video_id}"
    meta = probe_video_metadata(url)
    
    strategy = "CHAPTER" if meta.chapters else "SILENCE"
    
    result = {
        "video_id": video_id,
        "duration_sec": meta.duration,
        "chapters": [
            {
                "title": c.title,
                "start_time": c.start_time,
                "end_time": c.end_time
            }
            for c in meta.chapters
        ],
        "strategy": strategy,
        "title": meta.title,
        "uploader": meta.uploader,
    }
    
    logger.info(f"[probe_metadata] Done. Duration: {meta.duration}s, Strategy: {strategy}, Chapters: {len(meta.chapters)}")
    return result


# =============================================================================
# Job 2: Generate Candidates
# =============================================================================

def generate_candidates_job(
    video_id: str,
    youtube_video_id: str,
    duration_sec: float,
    chapters: Optional[List[dict]] = None,
    min_dur: Optional[float] = None,
    max_dur: Optional[float] = None,
    max_items: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Generate clip candidates from chapters or silence detection.
    
    Next job: transcribe_pass1_job
    Queue: io
    """
    logger.info(f"[generate_candidates] Starting for video: {video_id} (min={min_dur}, max={max_dur}, limit={max_items})")
    logger.info(f"[generate_candidates] Chapters payload: {type(chapters)} len={len(chapters) if chapters else 0}")
    
    # DEBUG: Explicitly log if params are None or values
    logger.info(f"DEBUG_PARAMS: min_dur={min_dur}, max_dur={max_dur}, max_items={max_items}")
    
    audio_path = None
    
    # If no chapters, we need audio for silence detection
    if not chapters or len(chapters) == 0:
        logger.info("[generate_candidates] No chapters, downloading audio for silence detection")
        url = f"https://www.youtube.com/watch?v={youtube_video_id}"
        audio_path = download_audio_only(url)
    
    candidates = generate_candidates(
        duration_sec=duration_sec,
        chapters=chapters,
        audio_path=audio_path,
        min_dur=min_dur,
        max_dur=max_dur,
        max_items=max_items,
    )
    
    result = [
        {
            "id": str(uuid4()),
            "start_sec": c.start_sec,
            "end_sec": c.end_sec,
            "strategy": c.strategy,
            "source_info": c.source_info
        }
        for c in candidates
    ]
    
    logger.info(f"[generate_candidates] Generated {len(result)} candidates")
    return result


# =============================================================================
# Job 3: Transcribe Pass 1 (Fast)
# =============================================================================

def transcribe_pass1_job(
    video_id: str,
    youtube_video_id: str,
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Fast transcription of candidate segments using Whisper tiny/small.
    
    Next job: llm_shortlist_job
    Queue: ai
    """
    import whisper
    import torch
    
    logger.info(f"[transcribe_pass1] Starting for {len(candidates)} candidates")
    
    # Load fast model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"[transcribe_pass1] Loading Whisper {settings.whisper_pass1_model} model on {device}...")
    model = whisper.load_model(settings.whisper_pass1_model, device=device)
    
    # Download full video for transcription
    from app.services.downloader import Downloader
    downloader = Downloader()
    url = f"https://www.youtube.com/watch?v={youtube_video_id}"
    dl_result = downloader.download_video(url)
    video_path = dl_result["video_path"]
    
    # Transcribe each candidate segment
    transcribed = []
    for cand in candidates[:settings.llm_send_max_candidates]:
        try:
            # Transcribe with segment bounds
            result = model.transcribe(
                video_path,
                language=None,  # Auto-detect
                beam_size=settings.whisper_pass1_beam,
                fp16=False,
            )
            
            # Extract text for this segment's time range
            text_parts = []
            for seg in result["segments"]:
                seg_start = seg["start"]
                seg_end = seg["end"]
                
                # Check overlap with candidate window
                if seg_end >= cand["start_sec"] and seg_start <= cand["end_sec"]:
                    text_parts.append(seg["text"].strip())
            
            cand["text"] = " ".join(text_parts)
            cand["transcript_pass1"] = cand["text"]
            transcribed.append(cand)
            
        except Exception as e:
            logger.error(f"[transcribe_pass1] Failed for candidate: {e}")
            continue
    
    # Cleanup
    import os
    if os.path.exists(video_path):
        os.remove(video_path)
    
    logger.info(f"[transcribe_pass1] Transcribed {len(transcribed)} candidates")
    return transcribed


# =============================================================================
# Job 4: LLM Shortlist (Stage 1)
# =============================================================================

def llm_shortlist_job(
    video_id: str,
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Use Groq LLM to select best clips from candidates.
    
    Next job: transcribe_pass2_job
    Queue: ai
    """
    from groq import Groq
    from app.core.settings import settings as main_settings
    
    logger.info(f"[llm_shortlist] Starting with {len(candidates)} candidates")
    
    # Format prompt
    system, user = format_shortlist_prompt(
        segments=candidates,
        max_clips=settings.llm_shortlist_max
    )
    
    # Call Groq
    client = Groq(api_key=main_settings.groq_api_key)
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    response_text = completion.choices[0].message.content
    result = json.loads(response_text)
    
    # Extract clips
    clips = result.get("clips", [])
    
    # Compute final scores
    scored_clips = []
    for clip in clips:
        text = ""
        # Find matching candidate text
        for cand in candidates:
            if abs(cand["start_sec"] - clip["start_sec"]) < 2:
                text = cand.get("text", "")
                break
        
        duration = clip["end_sec"] - clip["start_sec"]
        features = compute_final_score(
            llm_score=clip.get("viral_score", 0),
            text=text,
            risk_flags=clip.get("risk_flags", []),
            duration_sec=duration
        )
        
        clip["text"] = text
        clip["features_json"] = features
        clip["final_score"] = features["final_score"]
        scored_clips.append(clip)
    
    # Diversity filter
    items = [
        (str(i), c["final_score"], c.get("keywords", []))
        for i, c in enumerate(scored_clips)
    ]
    kept_indices = [int(i) for i in diversity_filter(items)]
    
    result_clips = [scored_clips[i] for i in kept_indices]
    
    logger.info(f"[llm_shortlist] Selected {len(result_clips)} clips after scoring and diversity filter")
    return result_clips


# =============================================================================
# Job 5: Transcribe Pass 2 (Accurate)
# =============================================================================

def transcribe_pass2_job(
    video_id: str,
    youtube_video_id: str,
    clips: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Accurate transcription for selected clips using better Whisper model.
    Includes word timing for karaoke subtitles.
    
    Next job: llm_refine_job
    Queue: ai
    """
    import whisper
    import torch
    
    logger.info(f"[transcribe_pass2] Starting for {len(clips)} clips")
    
    # Load fast model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"[transcribe_pass2] Loading Whisper {settings.whisper_pass2_model} model on {device}...")
    model = whisper.load_model(settings.whisper_pass2_model, device=device)
    
    # Download video
    from app.services.downloader import Downloader
    downloader = Downloader()
    url = f"https://www.youtube.com/watch?v={youtube_video_id}"
    dl_result = downloader.download_video(url)
    video_path = dl_result["video_path"]
    
    # Transcribe full video with word timing
    result = model.transcribe(
        video_path,
        language="id",
        beam_size=settings.whisper_pass2_beam,
        fp16=False,
        word_timestamps=True
    )
    
    # Map segments to clips
    for clip in clips:
        text_parts = []
        word_timing = []
        
        for seg in result["segments"]:
            seg_start = seg["start"]
            seg_end = seg["end"]
            
            if seg_end >= clip["start_sec"] and seg_start <= clip["end_sec"]:
                text_parts.append(seg["text"].strip())
                
                # Extract word timing if available
                for word in seg.get("words", []):
                    # Check for OVERLAP, not strict inclusion
                    if word["end"] > clip["start_sec"] and word["start"] < clip["end_sec"]:
                        word_timing.append({
                            "word": word["word"],
                            "start": word["start"] - clip["start_sec"],
                            "end": word["end"] - clip["start_sec"]
                        })
        
        clip["transcript_pass2"] = " ".join(text_parts)
        clip["word_timing"] = word_timing
    
    # Cleanup
    import os
    if os.path.exists(video_path):
        os.remove(video_path)
    
    logger.info(f"[transcribe_pass2] Completed for {len(clips)} clips")
    return clips


# =============================================================================
# Job 6: LLM Refine (Stage 2)
# =============================================================================

def llm_refine_job(clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Refine hook text and captions using LLM.
    
    Next job: render_preview_job
    Queue: ai
    """
    from groq import Groq
    from app.core.settings import settings as main_settings
    
    logger.info(f"[llm_refine] Starting for {len(clips)} clips")
    
    # Format prompt
    system, user = format_refine_prompt(clips)
    
    # Call Groq
    client = Groq(api_key=main_settings.groq_api_key)
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    
    response_text = completion.choices[0].message.content
    result = json.loads(response_text)
    
    refined = result.get("clips", [])
    
    # Merge refined data back
    for orig, ref in zip(clips, refined):
        orig["hook_text"] = ref.get("hook_text", orig.get("hook_text", ""))
        orig["caption"] = ref.get("caption", orig.get("caption", ""))
        orig["risk_flags"] = ref.get("risk_flags", orig.get("risk_flags", []))
        orig["keywords"] = ref.get("keywords", orig.get("keywords", []))
    
    logger.info(f"[llm_refine] Refined {len(clips)} clips")
    return clips


# =============================================================================
# Job 6.5: Validate Opening (Quality Gate)
# =============================================================================

def validate_opening_job(clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate clip openings using LLM.
    Marks clips with weak openings for potential re-cutting or flagging.
    
    Queue: ai
    """
    from groq import Groq
    from app.core.settings import settings as main_settings
    from app.services.groq_prompts import format_validate_opening_prompt
    
    logger.info(f"[validate_opening] Starting for {len(clips)} clips")
    
    client = Groq(api_key=main_settings.groq_api_key)
    
    for clip in clips:
        # Extract first 10 seconds of transcript from word timing
        words = clip.get("word_timing", [])
        opening_words = [w["word"] for w in words if w["end"] <= 10.0]
        
        # Fallback to transcript if no word timing
        if opening_words:
            opening_text = " ".join(opening_words)
        else:
            full_transcript = clip.get("transcript_pass2", "")
            # Estimate ~2.5 words per second -> 25 words for 10s
            opening_text = " ".join(full_transcript.split()[:25])
        
        duration = clip["end_sec"] - clip["start_sec"]
        
        # Skip validation for very short clips (< 30s)
        if duration < 30:
            clip["opening_validation"] = {"pass": True, "reason": "clip_too_short_to_validate"}
            continue
        
        # Format prompt
        system, user = format_validate_opening_prompt(opening_text, duration)
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(completion.choices[0].message.content)
            
            clip["opening_validation"] = {
                "pass": result.get("pass", True),
                "opening_type": result.get("opening_type", "unknown"),
                "reason": result.get("reason", ""),
                "confidence_score": result.get("confidence_score", 50)
            }
            
            if not result.get("pass", True):
                logger.warning(f"[validate_opening] WEAK opening: {clip.get('id', 'unknown')[:8]} - {result.get('reason', 'no reason')}")
                # Add risk flag
                existing_flags = clip.get("risk_flags", [])
                if "weak_opening" not in existing_flags:
                    clip["risk_flags"] = existing_flags + ["weak_opening"]
            else:
                logger.info(f"[validate_opening] PASS: {clip.get('id', 'unknown')[:8]} - {result.get('opening_type', 'unknown')}")
                
        except Exception as e:
            logger.error(f"[validate_opening] Failed for clip {clip.get('id', 'unknown')}: {e}")
            clip["opening_validation"] = {"pass": True, "reason": "validation_failed"}
    
    # Summary
    passed = sum(1 for c in clips if c.get("opening_validation", {}).get("pass", True))
    logger.info(f"[validate_opening] Completed: {passed}/{len(clips)} passed")
    return clips


# =============================================================================
# Job 6.6: Final Quality Control (Phase 3)
# =============================================================================

def _apply_recut(clip: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    """Apply recut plan by shifting start/end times."""
    shift_start = plan.get("shift_start_by_sec", 0.0)
    shift_end = plan.get("shift_end_by_sec", 0.0)
    
    # Ensure numeric values
    try:
        shift_start = float(shift_start) if shift_start else 0.0
        shift_end = float(shift_end) if shift_end else 0.0
    except (TypeError, ValueError):
        shift_start = 0.0
        shift_end = 0.0
    
    # Track offset for subtitle correction
    timing_offset = shift_start
    
    # Clamp shifts to ±3.0 seconds
    shift_start = max(-3.0, min(3.0, shift_start))
    shift_end = max(-3.0, min(3.0, shift_end))
    
    orig_start = clip["start_sec"]
    orig_end = clip["end_sec"]
    
    new_start = orig_start + shift_start
    new_end = orig_end + shift_end
    
    # Safety: Ensure valid duration (min 30s) and non-negative start
    if (new_end - new_start) >= 30.0 and new_start >= 0:
        logger.info(f"[Recut] {clip.get('id', 'unknown')[:8]}: {orig_start:.1f}->{new_start:.1f}, {orig_end:.1f}->{new_end:.1f}")
        clip["start_sec"] = new_start
        clip["end_sec"] = new_end
        clip["was_recut"] = True
        
        # Accumulate offset (important for subtitles)
        current_offset = clip.get("timing_offset", 0.0)
        clip["timing_offset"] = current_offset + timing_offset
    else:
        logger.warning(f"[Recut] Skipped (invalid result): {new_start:.1f}-{new_end:.1f}")
    
    return clip


def final_quality_control_job(clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Final QC: Evaluate opening + ending, apply auto-recut if needed.
    Drops clips that are fundamentally unfixable.
    
    Queue: ai
    """
    from groq import Groq
    from app.core.settings import settings as main_settings
    from app.services.groq_prompts import format_fqc_prompt
    
    logger.info(f"[FQC] Starting for {len(clips)} clips")
    client = Groq(api_key=main_settings.groq_api_key)
    
    passed_clips = []
    
    for clip in clips:
        words = clip.get("word_timing", [])
        duration = clip["end_sec"] - clip["start_sec"]
        
        # Extract opening (0-10s) and ending (last 12s) from word timing
        opening_words = [w["word"] for w in words if w["end"] <= 10.0]
        ending_start = max(0, duration - 12.0)
        ending_words = [w["word"] for w in words if w["start"] >= ending_start]
        
        # Fallback to transcript if no word timing
        opening_text = " ".join(opening_words) if opening_words else clip.get("transcript_pass2", "")[:150]
        ending_text = " ".join(ending_words) if ending_words else clip.get("transcript_pass2", "")[-150:]
        
        # Skip very short clips (< 30s)
        if duration < 30:
            clip["fqc_result"] = {"pass": True, "reason": "clip_too_short"}
            passed_clips.append(clip)
            continue
        
        system, user = format_fqc_prompt(
            clip.get("id", "unknown"),
            duration,
            opening_text,
            ending_text
        )
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(completion.choices[0].message.content)
            clip["fqc_result"] = result
            
            # Apply recut plan
            recut_plan = result.get("recut_plan", {})
            action = recut_plan.get("action", "none")
            
            if action == "drop":
                logger.warning(f"[FQC] DROPPED: {clip.get('id', 'unknown')[:8]} - {recut_plan.get('notes', 'unfixable')}")
                continue  # Skip this clip entirely
                
            elif action in ["shift_start", "shift_end", "shift_both"]:
                clip = _apply_recut(clip, recut_plan)
                clip["fqc_recut"] = True
                logger.info(f"[FQC] RECUT applied: {action}")
            else:
                logger.info(f"[FQC] PASS: No recut needed")
                
            passed_clips.append(clip)
            
        except Exception as e:
            logger.error(f"[FQC] Failed: {e}")
            passed_clips.append(clip) # Fallback: keep original
            
    logger.info(f"[FQC] Completed. {len(clips)} -> {len(passed_clips)} clips")
    return passed_clips


def final_packaging_job(clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Phase 4: Generate honest title, caption, and hashtags based on transcript.
    """
    from groq import Groq
    from app.core.settings import settings as main_settings
    from app.services.groq_prompts import format_packaging_prompt
    
    logger.info(f"[Packaging] Starting for {len(clips)} clips")
    client = Groq(api_key=main_settings.groq_api_key)
    
    for clip in clips:
        transcript = clip.get("transcript_pass2", "")
        duration = clip["end_sec"] - clip["start_sec"]
        
        if not transcript or len(transcript) < 50:
            logger.warning(f"[Packaging] Skipped (no transcript): {clip.get('id', 'unknown')[:8]}")
            continue
        
        system, user = format_packaging_prompt(
            clip.get("id", "unknown"),
            duration,
            transcript
        )
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(completion.choices[0].message.content)
            
            # Update clip dengan packaging data
            clip["key_sentence"] = result.get("key_sentence", "")
            clip["hook_text"] = result.get("title", clip.get("hook_text", ""))
            clip["suggested_caption"] = result.get("caption", clip.get("caption", ""))
            clip["hashtags"] = result.get("hashtags", [])
            clip["packaging_confidence"] = result.get("packaging_confidence", 50)
            
            logger.info(f"[Packaging] OK: {clip.get('id', 'unknown')[:8]} - '{result.get('title', '')[:30]}...'")
            
        except Exception as e:
            logger.error(f"[Packaging] Error: {e}")
    
    logger.info(f"[Packaging] Completed")
    return clips


# =============================================================================
# Job 7: Render Clips
# =============================================================================


def _snap_and_clean(clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Adjust start/end times using word timestamps to remove fillers and ensure clean cuts.
    """
    # Filler words set (mixture of ID/EN)
    FILLERS = {
        "eee", "ee", "hmm", "umm", "uh", "yak", "so", 
        "nah", "jadi", "okay", "oke", "terus", "berarti", 
        "actually", "like", "you know", "basically", "literally",
        "anu", "ngg", "yg", "yang"
    }
    
    cleaned_clips = []
    for c in clips:
        # If no word timing data, keep original
        words = c.get("word_timing", [])
        if not words:
            cleaned_clips.append(c)
            continue
            
        orig_start = c["start_sec"]
        
        # 1. Snap Start (Remove fillers)
        # word_timing is relative to orig_start (0.0 = orig_start)
        snap_start_rel = 0.0
        
        # Try to find the first non-filler word
        for w in words:
            # Simple cleaning: remove punctuation, lowercase
            clean_word = "".join(x for x in w["word"].lower() if x.isalpha())
            
            # If valid word (not filler, len > 1 or specific short words allowed)
            if clean_word not in FILLERS and (len(clean_word) > 1 or clean_word in ["i", "a", "di", "ke"]):
                snap_start_rel = w["start"]
                break
            # If filler, we consume it (loop continues)
        
        # 2. Snap End
        # Just snap to the end of the last word in the list to avoid silence tail
        snap_end_rel = words[-1]["end"]
        
        # 3. Apply Adjustment
        new_start = orig_start + snap_start_rel
        new_end = orig_start + snap_end_rel
        
        # Safety check: Don't make it too short (< 5s) or invalid
        if (new_end - new_start) >= 5.0:
            if abs(new_start - orig_start) > 0.1 or abs(new_end - c["end_sec"]) > 0.1:
                logger.info(f"[Snap] {c.get('id', 'unknown')}: {orig_start:.2f}->{new_start:.2f} (Cleaned start), {c['end_sec']:.2f}->{new_end:.2f} (Cleaned end)")
                
            c["start_sec"] = new_start
            c["end_sec"] = new_end
            
            # Update timing offset for subtitles
            # new_start is > orig_start, so we shifted start RIGHT (positive offset)
            offset = new_start - orig_start
            c["timing_offset"] = c.get("timing_offset", 0.0) + offset
            
        cleaned_clips.append(c)
        
    return cleaned_clips


def render_clips_job(
    video_id: str,
    youtube_video_id: str,
    clips: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Render actual MP4 files from clips.
    Downloads full video once, then cuts each clip with FFmpeg.
    
    Queue: render
    """
    import os
    import subprocess
    import glob
    from app.services.editor import Editor
    
    logger.info(f"[render_clips] Starting for {len(clips)} clips")

    # Apply Precision Trimming (Snap & Clean)
    clips = _snap_and_clean(clips)
    
    editor = Editor(output_dir="static/clips")
    url = f"https://www.youtube.com/watch?v={youtube_video_id}"
    
    # Download full video once (more reliable than section download)
    temp_dir = "/tmp/render_temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_video_template = f"{temp_dir}/{youtube_video_id}.%(ext)s"
    
    # Check if already downloaded
    existing = glob.glob(f"{temp_dir}/{youtube_video_id}.*")
    if existing:
        temp_video = existing[0]
        logger.info(f"[render_clips] Using cached video: {temp_video}")
    else:
        logger.info(f"[render_clips] Downloading full video...")
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", temp_video_template,
            "--no-playlist",
            url
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900  # 15 min timeout for large videos
        )
        
        # Find the downloaded file
        downloaded = glob.glob(f"{temp_dir}/{youtube_video_id}.*")
        if not downloaded:
            logger.error(f"[render_clips] Failed to download video: {result.stderr}")
            return []
        temp_video = downloaded[0]
        logger.info(f"[render_clips] Downloaded: {temp_video}")
    
    rendered_clips = []
    
    def _generate_srt(word_timing: List[Dict], start_sec: float) -> str:
        """Generate SRT content from word timings - Strict 1 Word Per Line (Karaoke)."""
        if not word_timing:
            return None
            
        srt_content = ""
        words = sorted(word_timing, key=lambda x: x["start"])
        
        # Helper for time format
        def fmt_time(t):
            import datetime
            # Ensure time is non-negative
            t = max(0, t)
            delta = datetime.timedelta(seconds=t)
            s = str(delta)
            if "." in s:
                base, decimal = s.split(".")
                decimal = decimal[:3]
            else:
                base = s
                decimal = "000"
            parts = base.split(":")
            if len(parts) == 2:
                base = f"0:{base}"
            return f"{base},{decimal}".replace("0:", "00:")

        entry_idx = 1
        for i, w in enumerate(words):
            # Apply offset to align with video that has been shifted/padded
            # If video start shifted +2s, word must appear +2s later in SRT time
            reshifted_start = w["start"] - start_sec # start_sec here is actuall the offset 
            # WAIT: word["start"] is relative to ORIGINAL start.
            # If we shifted Start by +2s, then the video slice starts 2s LATER.
            # So a word that was at 5s (relative) is now at 3s (relative) in the new slice?
            # NO. 
            # Original: Start=100. Word at 105 (rel=5).
            # New Start=102 (Shift=+2). Word still at 105.
            # New rel time = 105 - 102 = 3.
            # So: new_rel = old_rel - shift.
            
            # BUT: start_sec arg passed to this function is used as ADDITIVE offset in previous plan?
            # Let's stick to the plan: pass cumulative offset as 'start_sec' (bad name, but okay).
            # If Editor padded -1.5s (Start moved LEFT, e.g. 98.5).
            # Word at 105. New rel = 105 - 98.5 = 6.5.
            # So new_rel = old_rel - shift.
            # shift = -1.5. new_rel = 5 - (-1.5) = 6.5. Correct.
            
            # So we need: final_ts = w["start"] - total_shift_of_start_time
            # Passed arg 'start_sec' will be the total_shift.
            
            start_ts = fmt_time(w["start"] - start_sec)
            end_ts = fmt_time(w["end"] - start_sec)
            
            # Clean text (remove punctuation for clean look if desired, or keep)
            # Keeping punctuation for readability
            text = w["word"].strip().upper() 
            
            # SRT Entry
            # 1 word per line
            srt_content += f"{entry_idx}\n{start_ts} --> {end_ts}\n{text}\n\n"
            entry_idx += 1
                    
        return srt_content

    for i, clip in enumerate(clips):
        clip_id = clip.get("id", str(uuid4()))
        start = clip["start_sec"]
        end = clip["end_sec"]
        
        logger.info(f"[render_clips] Rendering clip {i+1}/{len(clips)}: {start}s - {end}s")
        
        srt_path = None
        try:
            # Generate SRT if word timing exists
            word_timing = clip.get("word_timing")
            if word_timing:
                # Calculate total shift applied to start_sec
                # 1. Pipeline recut/snap offsets (stored in timing_offset)
                # 2. Editor padding (-1.5s)
                
                # Total shift = timing_offset + (-1.5)
                # If timing_offset is +2.0 (start moved forward), and padding is -1.5 (start back)
                # Total change to start line = +0.5.
                # SRT timing calculation: new_time = old_time - total_shift
                
                pipeline_offset = clip.get("timing_offset", 0.0)
                editor_padding = -1.5 # Fixed in editor.py
                
                total_start_shift = pipeline_offset + editor_padding
                
                srt_content = _generate_srt(word_timing, total_start_shift)
                if srt_content:
                    srt_path = f"/tmp/{clip_id}.srt"
                    with open(srt_path, "w") as f:
                        f.write(srt_content)
            
            # Cut and process with FFmpeg
            output_path = editor.cut_video(
                input_path=temp_video,
                start=start,
                end=end,
                srt_path=srt_path
            )
            
            # Generate thumbnail
            thumb_path = editor.generate_thumbnail(output_path)
            
            # Update clip data
            clip["file_url"] = output_path
            clip["thumb_url"] = thumb_path
            rendered_clips.append(clip)
            
            logger.info(f"[render_clips] Rendered clip {clip_id}: {output_path}")
            
        except Exception as e:
            logger.error(f"[render_clips] Failed to render clip {clip_id}: {e}")
            continue
        finally:
            # Clean up SRT
            if srt_path and os.path.exists(srt_path):
                os.remove(srt_path)
    
    # Clean up temp video to save space
    if os.path.exists(temp_video):
        logger.info(f"[render_clips] Cleaning up source video: {temp_video}")
        os.remove(temp_video)
    
    logger.info(f"[render_clips] Completed: {len(rendered_clips)}/{len(clips)} clips rendered")
    return rendered_clips

