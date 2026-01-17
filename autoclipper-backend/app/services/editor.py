import ffmpeg
import logging
import os
from uuid import uuid4

logger = logging.getLogger(__name__)

class Editor:
    def __init__(self, output_dir: str = "static/clips"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def cut_video(self, input_path: str, start: float, end: float, srt_path: str = None) -> str:
        """
        Cut video segment, apply 9:16 Vertical Crop, optionally burn subtitles, and preserve audio.
        """
        clip_id = str(uuid4())
        output_path = os.path.join(self.output_dir, f"{clip_id}.mp4")
        
        try:
            # 1. Padding Logic
            start = max(0, start - 1.5)
            end = end + 1.5
            duration = end - start
            print(f"Cutting {duration}s from {start} to {end}")

            # 2. Input stream (with seek)
            input_stream = ffmpeg.input(input_path, ss=start, t=duration)
            
            # 3. Separate Video and Audio
            video = input_stream.video
            audio = input_stream.audio
            
            # 4. Apply video filters: Crop -> (Subtitles)
            video = video.filter('crop', w='ih*(9/16)', h='ih', x='(iw-ow)/2', y='0')
            
            if srt_path and os.path.exists(srt_path):
                # Middle Center, Small font (Requested style)
                style = "Alignment=2,Fontname=Arial,FontSize=16,PrimaryColour=&H00FFFF00,OutlineColour=&H00000000,BorderStyle=1,Outline=1,Shadow=1,MarginV=20"
                video = video.filter('subtitles', srt_path, force_style=style)

            # 5. Output with both video and audio (ultrafast preset for speed)
            output = ffmpeg.output(video, audio, output_path, vcodec='libx264', acodec='aac', preset='ultrafast', strict='experimental')
            ffmpeg.run(output, overwrite_output=True, quiet=True)
            
            return output_path
        except Exception as e:
            logger.error(f"FFmpeg cut failed: {e}")
            raise

    def generate_thumbnail(self, video_path: str) -> str:
        """
        Generate thumbnail from video.
        Returns thumbnail path.
        """
        output_path = video_path.replace(".mp4", ".jpg")
        try:
            (
                ffmpeg
                .input(video_path, ss=1)
                .output(output_path, vframes=1)
                .run(overwrite_output=True, quiet=True)
            )
            return output_path
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            raise
