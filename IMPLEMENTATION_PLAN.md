# Implementasi Plan: Final Packaging (Phase 4)

## Goal
Menghasilkan **judul, caption, dan hashtag yang jujur** berdasarkan transkrip final klip (setelah semua trimming dan validasi selesai). Tidak ada clickbait atau klaim berlebihan.

## Prinsip Utama
- Judul dan caption HARUS berdasarkan kalimat yang benar-benar ada di transkrip
- Tidak boleh menambahkan konteks yang tidak ada di video
- Tidak boleh melebih-lebihkan atau sensasionalisasi

---

## 1. Prompt Template (LLM)

**File:** `app/services/groq_prompts.py`

```python
PACKAGING_SYSTEM = """Kamu adalah editor media sosial senior yang menyiapkan paket upload FINAL dan JUJUR untuk video pendek (60–120 detik).

KONTEKS PENTING:
- Video sudah melewati editing, trimming, dan validasi kualitas.
- Ini BUKAN konten clickbait.
- Tugasmu: menyiapkan teks yang 100% sesuai dengan isi video.

TUGAS:
1) Identifikasi SATU kalimat kunci dari transkrip yang paling mewakili inti video.
   - Kalimat HARUS ada di transkrip (verbatim atau hampir sama).
   - JANGAN mengarang klaim baru.

2) Berdasarkan kalimat kunci tersebut, buat:
   a) JUDUL pendek dan jujur (maks 8 kata)
   b) CAPTION ringkas (maks 200 karakter)
   c) HASHTAGS:
      - 2 hashtag generik
      - 3-4 hashtag spesifik topik
      - Tidak ada tag menyesatkan

3) Judul dan caption HARUS:
   - Sesuai dengan isi video
   - Tidak menjanjikan hasil yang tidak ada di video
   - Cocok untuk TikTok / Reels / Shorts

OUTPUT FORMAT (JSON ONLY):
{
  "key_sentence": "...",
  "title": "...",
  "caption": "...",
  "hashtags": ["#...", "#...", "#...", "#...", "#..."],
  "packaging_confidence": 0-100
}

ATURAN:
- JANGAN menambahkan konteks yang tidak ada di transkrip.
- JANGAN melebih-lebihkan atau sensasionalisasi.
- Jika transkrip tidak jelas, turunkan confidence score.
- JANGAN jelaskan apapun di luar JSON."""

PACKAGING_USER_TEMPLATE = """CLIP ID: {clip_id}
DURASI: {duration_sec:.1f} detik

TRANSKRIP FINAL:
\"\"\"{transcript}\"\"\"

Respond in JSON only."""


def format_packaging_prompt(clip_id: str, duration_sec: float, 
                            transcript: str) -> tuple[str, str]:
    user = PACKAGING_USER_TEMPLATE.format(
        clip_id=clip_id[:8] if clip_id else "unknown",
        duration_sec=duration_sec,
        transcript=transcript[:1500]
    )
    return PACKAGING_SYSTEM, user
```

---

## 2. Job Function

**File:** `app/workers/pipeline_v2.py`

```python
def final_packaging_job(clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate honest title, caption, and hashtags based on transcript.
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
            clip["caption"] = result.get("caption", clip.get("caption", ""))
            clip["hashtags"] = result.get("hashtags", [])
            clip["packaging_confidence"] = result.get("packaging_confidence", 50)
            
            logger.info(f"[Packaging] OK: {clip.get('id', 'unknown')[:8]} - '{result.get('title', '')[:30]}...'")
            
        except Exception as e:
            logger.error(f"[Packaging] Error: {e}")
    
    logger.info(f"[Packaging] Completed")
    return clips
```

---

## 3. Integrasi ke Pipeline

**File:** `app/workers/orchestrator.py`

Panggil `final_packaging_job` setelah `final_quality_control_job` dan sebelum `render_clips_job`:

```python
def orchestrated_llm_refine(video_id: str, youtube_video_id: str, clips: list):
    try:
        # Step 1: Validate openings
        clips = validate_opening_job(clips)
        
        # Step 2: LLM Refine
        refined = llm_refine_job(clips)
        
        # Step 3: Final Quality Control
        qc_passed = final_quality_control_job(refined)
        
        # Step 4: Final Packaging (NEW)
        from app.workers.pipeline_v2 import final_packaging_job
        packaged = final_packaging_job(qc_passed)
        
        # Step 5: Render
        rendered = render_clips_job(video_id, youtube_video_id, packaged)
        # ...
```

---

## 4. Flow Diagram

```
┌──────────────────────────────┐
│ final_quality_control_job   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│   final_packaging_job       │ ← Phase 4 (NEW)
│  - Extract key sentence     │
│  - Generate honest title    │
│  - Generate caption         │
│  - Generate hashtags        │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│     render_clips_job        │
└──────────────────────────────┘
```

---

## 5. Verifikasi
1.  Proses video baru.
2.  Cek log `[Packaging] OK`.
3.  Verifikasi di database/UI bahwa `hook_text`, `caption`, `hashtags` terisi.
4.  Pastikan judul dan caption sesuai dengan isi transkrip.
