"""
Candidate Segment Generator Service
Generate clip candidates from chapters or silence detection.
"""
from __future__ import annotations

import re
import subprocess
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.core.settings_v2 import refactor_settings as settings

logger = logging.getLogger(__name__)

@dataclass
class Candidate:
    start_sec: float
    end_sec: float
    strategy: str  # "CHAPTER" or "SILENCE"
    source_info: str = ""  # e.g., chapter title

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def candidates_from_chapters(
    duration_sec: float,
    chapters: List[dict],
    min_dur: Optional[float] = None,
    max_dur: Optional[float] = None,
    max_items: Optional[int] = None,
) -> List[Candidate]:
    """
    Create candidate windows from video chapters.
    Each chapter boundary becomes potential clip start points.
    
    Args:
        duration_sec: Total video duration
        chapters: List of {title, start_time, end_time}
        max_items: Max number of candidates to return
        
    Returns:
        List of Candidate segments
    """
    min_len = min_dur or settings.cand_min_sec
    max_len = max_dur or settings.cand_max_sec
    shift = settings.cand_shift_sec
    limit = max_items or settings.cand_max_per_video

    out: List[Candidate] = []
    
    for ch in chapters:
        s = float(ch.get("start_time") or 0.0)
        e = float(ch.get("end_time") or 0.0)
        title = str(ch.get("title") or "")
        
        if e <= s:
            continue
            
        chapter_len = e - s

        # Choose window length within [min_len, max_len]
        win = _clamp(chapter_len, min_len, max_len)
        
        # Create shifted windows inside chapter
        for offset in range(0, int(chapter_len), shift):
            start = s + offset
            end = start + win
            
            # Clamp to chapter and video bounds
            if end > e:
                end = e
                start = max(s, end - win)
                
            start = _clamp(start, 0.0, duration_sec)
            end = _clamp(end, 0.0, duration_sec)
            
            if end - start >= min_len:
                out.append(Candidate(
                    start_sec=start,
                    end_sec=end,
                    strategy="CHAPTER",
                    source_info=title
                ))

    # Limit total candidates
    return out[:limit]


def _parse_silencedetect(stderr_text: str) -> List[Tuple[float, float]]:
    """
    Parse ffmpeg silencedetect output to find silence intervals.
    
    Returns:
        List of (silence_start, silence_end) tuples
    """
    silences: List[Tuple[float, float]] = []
    s_start: Optional[float] = None

    for line in stderr_text.splitlines():
        # Match: [silencedetect @ ...] silence_start: 12.345
        m1 = re.search(r"silence_start:\s*([0-9.]+)", line)
        if m1:
            s_start = float(m1.group(1))
            continue
            
        # Match: [silencedetect @ ...] silence_end: 14.567
        m2 = re.search(r"silence_end:\s*([0-9.]+)", line)
        if m2 and s_start is not None:
            s_end = float(m2.group(1))
            silences.append((s_start, s_end))
            s_start = None
            
    return silences


def candidates_from_silence(
    audio_path: str,
    duration_sec: float,
    silence_db: int = -35,
    min_silence_sec: float = 0.35,
    min_dur: Optional[float] = None,
    max_dur: Optional[float] = None,
    max_items: Optional[int] = None,
) -> List[Candidate]:
    """
    Use ffmpeg silencedetect to find speech blocks, then create candidate windows.
    Speech blocks are the gaps between silence.
    
    Args:
        audio_path: Path to audio file
        duration_sec: Total duration
        silence_db: Silence threshold in dB (default -35)
        min_silence_sec: Minimum silence duration to detect
        max_items: Max number of candidates to return
        
    Returns:
        List of Candidate segments
    """
    logger.info(f"Running silence detection on: {audio_path}")
    limit = max_items or settings.cand_max_per_video
    
    cmd = [
        "ffmpeg",
        "-i", audio_path,
        "-af", f"silencedetect=n={silence_db}dB:d={min_silence_sec}",
        "-f", "null",
        "-"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
    except subprocess.TimeoutExpired:
        logger.error("Silence detection timed out")
        return []
    
    silences = _parse_silencedetect(result.stderr)
    logger.info(f"Found {len(silences)} silence intervals")

    # Build speech blocks (gaps between silences)
    speech_blocks: List[Tuple[float, float]] = []
    silences = sorted(silences, key=lambda t: t[0])
    
    cur = 0.0
    for s0, s1 in silences:
        if s0 > cur + 1.0:  # At least 1 second of speech
            speech_blocks.append((cur, s0))
        cur = max(cur, s1)
        
    if cur < duration_sec - 1.0:
        speech_blocks.append((cur, duration_sec))

    logger.info(f"Found {len(speech_blocks)} speech blocks")

    # Generate candidate windows from speech blocks
    min_len = min_dur or settings.cand_min_sec
    max_len = max_dur or settings.cand_max_sec
    shift = settings.cand_shift_sec

    out: List[Candidate] = []
    
    for b0, b1 in speech_blocks:
        block_len = b1 - b0
        
        if block_len < min_len:
            continue
            
        win = _clamp(block_len, min_len, max_len)
        
        # Slide window through block
        t = b0
        while t + min_len <= b1:
            start = t
            end = min(t + win, b1)
            
            if end - start >= min_len:
                out.append(Candidate(
                    start_sec=start,
                    end_sec=end,
                    strategy="SILENCE",
                    source_info=f"speech_{int(b0)}s"
                ))
            t += shift
            
    return out[:limit]


def generate_candidates(
    duration_sec: float,
    chapters: Optional[List[dict]] = None,
    audio_path: Optional[str] = None,
    min_dur: Optional[float] = None,
    max_dur: Optional[float] = None,
    max_items: Optional[int] = None,
) -> List[Candidate]:
    """
    Main entry point: generate candidates using chapters if available,
    otherwise fall back to silence detection.
    
    Args:
        duration_sec: Video duration
        chapters: Optional list of chapters
        audio_path: Required if no chapters (for silence detection)
        max_items: Max candidates to return
        
    Returns:
        List of Candidate segments
    """
    if chapters and len(chapters) > 0:
        logger.info(f"Using CHAPTER strategy (min={min_dur}, max={max_dur}, limit={max_items})")
        return candidates_from_chapters(duration_sec, chapters, min_dur, max_dur, max_items)
    else:
        if not audio_path:
            raise ValueError("audio_path required when no chapters available")
    
    # Try silence detection
    results = candidates_from_silence(audio_path, duration_sec, min_dur=min_dur, max_dur=max_dur, max_items=max_items)
    
    if results:
        return results
        
    # Fallback to fixed intervals if silence detection yielded nothing
    logger.warning("SILENCE strategy returned 0 candidates. Falling back to FIXED_INTERVAL strategy.")
    return candidates_from_fixed_intervals(duration_sec, min_dur=min_dur, max_dur=max_dur, max_items=max_items)


def candidates_from_fixed_intervals(
    duration_sec: float,
    min_dur: Optional[float] = None,
    max_dur: Optional[float] = None,
    max_items: Optional[int] = None,
) -> List[Candidate]:
    """
    Fallback strategy: Generate clips at fixed intervals.
    Used when chapters are missing AND silence detection fails.
    """
    min_len = min_dur or settings.cand_min_sec
    max_len = max_dur or settings.cand_max_sec
    shift = settings.cand_shift_sec
    limit = max_items or settings.cand_max_per_video
    
    out: List[Candidate] = []
    
    t = 0.0
    while t + min_len < duration_sec:
        start = t
        end = min(t + max_len, duration_sec)
        
        if end - start >= min_len:
            out.append(Candidate(
                start_sec=start,
                end_sec=end,
                strategy="FIXED_INTERVAL",
                source_info=f"interval_{int(t)}s"
            ))
        
        t += shift
        
    logger.info(f"Using FIXED_INTERVAL strategy: generated {len(out)} candidates")
    return out[:limit]
