import os
import yt_dlp
import logging
from uuid import uuid4

logger = logging.getLogger(__name__)

class Downloader:
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = os.path.abspath(download_dir)
        os.makedirs(self.download_dir, exist_ok=True)

    def download_video(self, url: str) -> dict:
        """
        Download video from YouTube URL.
        Returns dict with file_path and metadata.
        """
        video_id = str(uuid4())
        output_template = os.path.join(self.download_dir, f"{video_id}.%(ext)s")
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # yt-dlp might merge to different ext, verify existence
                if not os.path.exists(filename):
                    # Check for .mp4 if merged
                    base = os.path.splitext(filename)[0]
                    if os.path.exists(f"{base}.mp4"):
                        filename = f"{base}.mp4"
                
                return {
                    "video_path": filename,
                    "title": info.get('title'),
                    "duration": info.get('duration'),
                    "uploader": info.get('uploader'),
                    "original_url": url
                }
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
