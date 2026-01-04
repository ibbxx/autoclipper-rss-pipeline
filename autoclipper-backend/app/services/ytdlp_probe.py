"""
yt-dlp Metadata Probe Service
Probe video metadata (duration, chapters) via yt-dlp JSON without downloading full video.
"""
from __future__ import annotations

import json
import subprocess
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class YtdlpChapter:
    title: str
    start_time: float
    end_time: float

@dataclass
class YtdlpMeta:
    video_id: str
    title: str
    duration: Optional[float]
    uploader: Optional[str]
    chapters: List[YtdlpChapter]
    raw: Dict[str, Any]

def probe_video_metadata(url: str) -> YtdlpMeta:
    """
    Uses yt-dlp JSON output to fetch video metadata quickly.
    Does NOT download the video, only fetches info.
    
    Args:
        url: YouTube video URL or ID
        
    Returns:
        YtdlpMeta with duration, chapters, and raw metadata
    """
    logger.info(f"Probing metadata for: {url}")
    
    cmd = ["yt-dlp", "-J", "--no-download", url]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )
        data = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout probing metadata for: {url}")
        raise RuntimeError("yt-dlp metadata probe timed out")
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed: {e.stderr}")
        raise RuntimeError(f"yt-dlp failed: {e.stderr}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse yt-dlp JSON: {e}")
        raise RuntimeError("Invalid JSON from yt-dlp")

    # Parse chapters
    chapters: List[YtdlpChapter] = []
    for ch in (data.get("chapters") or []):
        try:
            chapters.append(
                YtdlpChapter(
                    title=str(ch.get("title") or ""),
                    start_time=float(ch.get("start_time") or 0.0),
                    end_time=float(ch.get("end_time") or 0.0),
                )
            )
        except (TypeError, ValueError):
            continue

    return YtdlpMeta(
        video_id=str(data.get("id") or ""),
        title=str(data.get("title") or ""),
        duration=(float(data["duration"]) if data.get("duration") is not None else None),
        uploader=(str(data.get("uploader")) if data.get("uploader") else None),
        chapters=chapters,
        raw=data,
    )


def download_audio_only(url: str, output_dir: str = "temp_downloads") -> str:
    """
    Download audio-only stream for silence detection.
    Much faster than downloading full video.
    
    Returns:
        Path to downloaded audio file
    """
    import os
    from uuid import uuid4
    
    os.makedirs(output_dir, exist_ok=True)
    audio_id = str(uuid4())
    output_template = os.path.join(output_dir, f"{audio_id}.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "-o", output_template,
        "--no-playlist",
        url
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=300
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Audio download timed out")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Audio download failed: {e.stderr}")
    
    # Find the downloaded file
    for ext in ["m4a", "webm", "mp3", "opus"]:
        path = os.path.join(output_dir, f"{audio_id}.{ext}")
        if os.path.exists(path):
            return path
    
    raise RuntimeError("Downloaded audio file not found")
