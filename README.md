# AutoClipper - RSS Pipeline

Platform otomatisasi pembuatan short-form content dari YouTube ke TikTok.

## Fitur
- Monitor channel YouTube secara otomatis (RSS feed)
- Download video baru dengan yt-dlp
- Transcription dengan OpenAI Whisper
- AI analysis untuk deteksi momen viral (Groq Llama 3.3)
- Auto-crop 9:16 untuk TikTok
- Karaoke-style subtitles
- Dashboard untuk preview dan approve clips

## Tech Stack
- **Backend:** FastAPI + PostgreSQL + Redis Queue
- **Frontend:** Next.js 16 + TanStack Query + Tailwind CSS
- **AI:** Whisper + Groq API
- **Video:** yt-dlp + FFmpeg

## Quick Start
```bash
./start-dev.sh
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Requirements
- Docker Desktop
- Node.js 18+
