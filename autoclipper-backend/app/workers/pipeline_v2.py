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
    
    logger.info(f"[transcribe_pass1] Starting for {len(candidates)} candidates")
    
    # Load fast model
    model = whisper.load_model(settings.whisper_pass1_model, device="cpu")
    
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
    
    logger.info(f"[transcribe_pass2] Starting for {len(clips)} clips")
    
    # Load better model
    model = whisper.load_model(settings.whisper_pass2_model, device="cpu")
    
    # Download video
    from app.services.downloader import Downloader
    downloader = Downloader()
    url = f"https://www.youtube.com/watch?v={youtube_video_id}"
    dl_result = downloader.download_video(url)
    video_path = dl_result["video_path"]
    
    # Transcribe full video with word timing
    result = model.transcribe(
        video_path,
        language=None,
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
# Job 7: Render Clips
# =============================================================================

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
            start_ts = fmt_time(w["start"])
            end_ts = fmt_time(w["end"])
            
            # Clean text (remove punctuation for clean look if desired, or keep)
            # Keeping punctuation for readability
            text = w["word"].strip() 
            
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
                srt_content = _generate_srt(word_timing, 0) # timing is relative to clip start
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

