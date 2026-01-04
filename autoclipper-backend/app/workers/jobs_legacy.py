import logging
import os
from uuid import uuid4
from app.db.context import get_db_session
from app.db.repositories import VideoRepository, ClipRepository, PostJobRepository
from app.core.enums import VideoStatus, RenderStatus, PostStatus

# Services
from app.services.downloader import Downloader
from app.services.transcriber import Transcriber
from app.services.intelligence import Intelligence
from app.services.editor import Editor

logger = logging.getLogger(__name__)

# Lazy loading services
_services = {}

def get_services():
    if not _services:
        logger.info("Initializing AI Services...")
        _services["downloader"] = Downloader(download_dir="temp_downloads")
        # Load Whisper model (might download on first run)
        _services["transcriber"] = Transcriber(model_size="base")
        _services["intelligence"] = Intelligence()
        _services["editor"] = Editor(output_dir="static/clips")
    return _services

def process_video_job(video_id: str) -> None:
    """
    Process a video using AI pipeline.
    """
    logger.info(f"Processing video: {video_id}")
    
    with get_db_session() as db:
        video_repo = VideoRepository(db)
        clip_repo = ClipRepository(db)
        
        video = video_repo.get_by_id(video_id)
        if not video:
            logger.warning(f"Video not found: {video_id}")
            return
        
        try:
            # Initialize services here to catch startup errors inside the job
            services = get_services()
            downloader = services["downloader"]
            transcriber = services["transcriber"]
            intelligence = services["intelligence"]
            editor = services["editor"]

            # 1. Update Status
            video.status = VideoStatus.PROCESSING.value
            video.progress = 10
            db.commit()
            
            # 2. Download
            logger.info("Step 1/4: Downloading...")
            yt_url = f"https://www.youtube.com/watch?v={video.youtube_video_id}"
            dl_result = downloader.download_video(yt_url)
            local_video_path = dl_result["video_path"]
            
            video.progress = 30
            db.commit()

            # 3. Transcribe
            logger.info("Step 2/4: Transcribing...")
            transcript = transcriber.transcribe(local_video_path)
            
            video.progress = 50
            db.commit()

            # 4. Analyze
            logger.info("Step 3/4: Analyzing with AI...")
            clip_candidates = intelligence.analyze_transcript(transcript)
            
            video.progress = 70
            db.commit()

            # 5. Cut & Save
            logger.info(f"Step 4/4: Cutting {len(clip_candidates)} clips...")
            
            clip_repo.delete_by_video(video_id)
            
            for i, cand in enumerate(clip_candidates):
                raw_start = float(cand.get("start_timestamp", 0))
                raw_end = float(cand.get("end_timestamp", 0))
                
                if raw_end <= raw_start: continue

                # Padded start/end (must match editor padding)
                start = max(0, raw_start - 1.5)
                end = raw_end + 1.5
                
                # Generate SRT content for this specific clip (2-word Karaoke style)
                srt_content = ""
                srt_counter = 1
                
                def fmt_time(t):
                    t = max(0, t)
                    hours = int(t // 3600)
                    minutes = int((t % 3600) // 60)
                    seconds = int(t % 60)
                    millis = int((t * 1000) % 1000)
                    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"
                
                for seg in transcript:
                    seg_start = float(seg['start'])
                    seg_end = float(seg['end'])
                    
                    # Include segments that overlap with the clip window
                    if seg_end >= start and seg_start <= end:
                        rel_start = max(0, seg_start - start)
                        rel_end = seg_end - start
                        seg_duration = rel_end - rel_start
                        
                        # Split text into 1-word chunks (Karaoke Style)
                        all_words = seg['text'].split()
                        
                        # Fix speeding text: Trim words if segment is partially cut
                        full_seg_duration = seg_end - seg_start
                        if full_seg_duration > 0:
                            # If start is cut
                            if seg_start < start:
                                kept_ratio = (seg_end - start) / full_seg_duration
                                keep_count = int(len(all_words) * kept_ratio)
                                all_words = all_words[-keep_count:] if keep_count > 0 else []
                            
                            # If end is cut
                            if seg_end > end:
                                kept_ratio = (end - seg_start) / full_seg_duration
                                keep_count = int(len(all_words) * kept_ratio)
                                all_words = all_words[:keep_count] if keep_count > 0 else []

                        chunks = all_words # 1 word per chunk
                        
                        if not chunks:
                            continue
                        
                        # Distribute timing evenly across chunks
                        chunk_duration = seg_duration / len(chunks)
                        for k, chunk in enumerate(chunks):
                            chunk_start = rel_start + (k * chunk_duration)
                            chunk_end = chunk_start + chunk_duration
                            
                            srt_content += f"{srt_counter}\n"
                            srt_content += f"{fmt_time(chunk_start)} --> {fmt_time(chunk_end)}\n"
                            srt_content += f"{chunk.upper()}\n\n"
                            srt_counter += 1
                
                # Save SRT to temp file
                srt_path = f"temp_downloads/{video_id}_{i}.srt"
                with open(srt_path, "w") as f:
                    f.write(srt_content)
                
                output_path = editor.cut_video(local_video_path, raw_start, raw_end, srt_path=srt_path)
                
                # Cleanup SRT
                if os.path.exists(srt_path):
                    os.remove(srt_path)

                thumb_path = editor.generate_thumbnail(output_path)
                
                # Use full URL for local dev (Frontend on port 3000, Backend on 8000)
                base_url = "http://localhost:8000"
                file_url = f"{base_url}/static/clips/{os.path.basename(output_path)}"
                thumb_url = f"{base_url}/static/clips/{os.path.basename(thumb_path)}"
                
                clip_repo.create(
                    id=str(uuid4()),
                    video_id=video_id,
                    start_sec=start,
                    end_sec=end,
                    score=float(cand.get("virality_score", 0)),
                    render_status=RenderStatus.READY.value,
                    file_url=file_url,
                    thumb_url=thumb_url,
                    suggested_caption=cand.get("suggested_caption", ""),
                    approved=False
                )

            # Cleanup
            if os.path.exists(local_video_path):
                os.remove(local_video_path)

            video.status = VideoStatus.READY.value
            video.progress = 100
            video.error_message = None
            db.commit()
            logger.info(f"Video processed successfully: {video_id}")
            
        except Exception as e:
            logger.error(f"Error processing video {video_id}: {e}")
            video.status = VideoStatus.ERROR.value
            video.error_message = str(e)
            db.commit()
            raise

def upload_tiktok_job(post_job_id: str) -> None:
    # ... placeholder ...
    pass
