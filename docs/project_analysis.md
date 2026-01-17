# AutoClipper Project Analysis

## 1. Project Overview
**AutoClipper** is an automated pipeline designed to monitor YouTube channels, download new videos, and intelligently process them into short-form content (9:16 vertical video) suitable for TikTok/Reels/Shorts. 

It leverages **AI (LLMs)** for content curation and **Whisper** for transcription, ensuring that clips are not only viral-worthy but also perfectly cropped and subtitled.

## 2. Technology Stack

### Backend
- **Framework**: FastAPI (Python) - High performance async API.
- **Database**: PostgreSQL - Relational data (Channels, Videos, Clips).
- **Queue/Async**: Redis + RQ (suspected/implied) or custom worker loop.
- **AI Processing**: 
    - **Transcription**: OpenAI Whisper (Local GPU execution).
    - **Intelligence**: Groq API (Llama-3.3-70b-versatile) for scoring, refining, and packaging.
- **Media Processing**: `yt-dlp` (download), `ffmpeg` (cutting/cropping).
- **Containerization**: Docker & Docker Compose.

### Frontend
- **Framework**: Next.js 16 (App Router).
- **Styling**: Tailwind CSS.
- **State Management**: TanStack Query (React Query).
- **UI Components**: Likely Shadcn/UI or custom based on structure.

## 3. Architecture & Pipeline (Backend)

The core logic resides in `autoclipper-backend/app/workers/pipeline_v2.py`, which implements a "Segment-First" processing approach.

### The Pipeline Steps (V2)

1.  **Probe Metadata** (`probe_metadata_job`)
    -   Fetches video duration, chapters, and metadata using `yt-dlp`.
    -   Decides strategy: `CHAPTER` or `SILENCE`.

2.  **Generate Candidates** (`generate_candidates_job`)
    -   Splits video into "Candidate Segments" based on YouTube Chapters or Silence Detection.
    -   Result: A list of rough time ranges.

3.  **Transcribe Pass 1** (`transcribe_pass1_job`)
    -   **Fast Mode**: Uses a smaller Whisper model (e.g., `tiny` or `small`).
    -   Goals: Get rough text for LLM scoring.

4.  **LLM Shortlist** (`llm_shortlist_job`)
    -   **AI**: Groq (Llama 3.3).
    -   Input: Candidate segments + Pass 1 transcripts.
    -   Output: "Viral Score", initial reasoning.
    -   **Diversity Filter**: Ensures clips aren't too similar.

5.  **Transcribe Pass 2** (`transcribe_pass2_job`)
    -   **Accurate Mode**: Uses a larger Whisper model (e.g., `medium` or `large`).
    -   **Features**: Enables `word_timestamps` for karaoke-style subtitles.

6.  **LLM Refine & Validation** (`orchestrated_llm_refine`)
    -   **Refining** (`llm_refine_job`): Polish hook text and captions.
    -   **Opening Validation** (`validate_opening_job`): checks if the first 0-10s are engaging.
    -   **Final QC** (`final_quality_control_job`): Checks start/end boundaries, applies auto-recuts (shifts start/end by ±3s) if needed.
    -   **Final Packaging** (`final_packaging_job` - *Phase 4*): Generates honest titles/captions/hashtags based on the final transcript.

7.  **Render** (`render_clips_job`)
    -   Downloads full high-quality video.
    -   **Snap & Clean**: Adjusts cut points to nearest word boundaries to remove filler words ("um", "uh") and avoid cutting words in half.
    -   Outputs: MP4 files + SRT subtitles.

## 4. Key Data Models (`app/models`)

-   **Channel**: YouTube channel to monitor.
-   **Video**: A specific YouTube video being processed.
-   **Clip**: The central unit of work. Contains:
    -   `transcript_pass1`, `transcript_pass2`
    -   `word_timing_json` (for subtitles)
    -   `llm_viral_score`, `final_score`
    -   `packaging_confidence`, `hook_text`, `hashtags`
    -   `render_status`

## 5. Folder Structure Highlights

```
/
├── autoclipper-backend/
│   ├── app/
│   │   ├── workers/
│   │   │   ├── pipeline_v2.py    # CORE LOGIC
│   │   │   └── orchestrator.py   # Job sequencing
│   │   ├── services/
│   │   │   ├── groq_prompts.py   # Prompt engineering
│   │   │   ├── downloader.py     # yt-dlp wrapper
│   │   │   └── transcriber.py    # Whisper wrapper
│   │   └── models/               # SQLAlchemy definitions
│   └── Dockerfile
├── autoclipper-frontend/
│   ├── src/
│   │   ├── app/                  # Next.js Pages
│   │   └── lib/                  # API clients
│   └── package.json
└── scripts/                      # Startup/Setup scripts
```

## 6. Current State & Implementation Plan
-   The project is actively implementing **Phase 4: Final Packaging**.
-   **Goal**: Ensure generated metadata (titles, captions) is "Honest" (non-clickbait) and derived strictly from the transcript.
-   **Status**: `final_packaging_job` is implemented in `pipeline_v2.py` but needs to be fully integrated into the orchestrator and UI.
