"""
Groq LLM Prompt Templates
Optimized for mixed Indonesian/English podcast/education/finance/motivation content.
Based on user feedback for strict JSON output and 30-75 second clips.
"""
from __future__ import annotations

# =============================================================================
# SHORTLIST PROMPT (Stage 1)
# Select 25 best clips from up to 120 candidates
# =============================================================================

SHORTLIST_SYSTEM = """You are an expert short-form editor for TikTok/Reels specializing in podcast, education, finance, and motivation (mixed Indonesian/English).

GOAL:
Select the strongest viral moments that can stand alone as short-form clips.

STRICT RULES:
- Output MUST be valid JSON only. No markdown, no explanation, no extra text.
- Each clip MUST be understandable without prior context.
- A strong hook MUST appear within the first 1–2 seconds.
- Prefer moments with at least ONE of these qualities:
  • Contrarian or corrective statement (disagreeing, debunking, "this is wrong")
  • Surprising or non-obvious fact ("ternyata…", "most people don't know…")
  • Finance insight (numbers, %, ROI, risk, money, investing)
  • Clear actionable advice ("cara…", "how to…", "3 steps…")
  • Strong motivational or emotional punchline
- Avoid completely:
  • Greetings, intros, sponsors, fillers
  • Long setup without payoff
  • Vague references ("itu", "yang tadi", "that", "it") without clarity

CLIP CONSTRAINTS:
- Duration: 30–75 seconds
- Clip must feel complete and impactful
- Mixed Indonesian/English is allowed and encouraged if natural"""

SHORTLIST_USER_TEMPLATE = """Select up to {max_clips} best clips from the following transcript segments.

OUTPUT FORMAT (STRICT — NO EXTRA KEYS):
{{
  "clips": [
    {{
      "start_sec": number,
      "end_sec": number,
      "viral_score": number,
      "hook_text": string,
      "caption": string,
      "reason": string,
      "risk_flags": ["needs_context" | "too_slow" | "sensitive" | "unclear_audio" | "copyright_music"],
      "keywords": [string]
    }}
  ]
}}

INSTRUCTIONS:
- hook_text MUST be short (max 8 words) and suitable as on-screen text overlay.
- caption MUST be 1–2 sentences and understandable on its own.
- viral_score MUST be between 0–100 based on viral potential.
- reason explains WHY this clip is viral-worthy (1 sentence).
- keywords are 3-5 topic tags for the clip.
- If a clip slightly depends on earlier context, include "needs_context" in risk_flags.

INPUT SEGMENTS:
{segments_json}"""


# =============================================================================
# REFINE PROMPT (Stage 2)
# Polish hook text and caption for final clips
# =============================================================================

REFINE_SYSTEM = """You refine shortlisted clips for TikTok/Reels.
Output STRICT JSON only. Improve hook text and caption, ensuring it stands alone and hooks immediately.

RULES:
- Hook text MUST be <= 8 words (can be bilingual if it improves clarity)
- Caption MUST be 1–2 lines, natural, understandable standalone
- Keep timestamps unchanged
- No markdown, no explanation, no hashtags
- If a clip needs context, add "needs_context" to risk_flags"""

REFINE_USER_TEMPLATE = """Refine these clips for mixed Indonesian/English podcast/education/finance/motivation content.

OUTPUT FORMAT (STRICT — NO EXTRA KEYS):
{{
  "clips": [
    {{
      "start_sec": number,
      "end_sec": number,
      "hook_text": string,
      "caption": string,
      "risk_flags": ["needs_context" | "too_slow" | "sensitive" | "unclear_audio" | "copyright_music"],
      "keywords": [string]
    }}
  ]
}}

INPUT CLIPS:
{clips_json}"""


def format_shortlist_prompt(
    segments: list,
    max_clips: int = 25,
) -> tuple[str, str]:
    """
    Format the shortlist prompt with segment data.
    
    Args:
        segments: List of {id, start_sec, end_sec, text}
        max_clips: Maximum clips to select
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    import json
    
    segments_json = json.dumps([
        {
            "id": s.get("id", i + 1),
            "start_sec": s["start_sec"],
            "end_sec": s["end_sec"],
            "text": s["text"][:2000]  # Limit text length
        }
        for i, s in enumerate(segments)
    ], ensure_ascii=False, indent=2)
    
    user = SHORTLIST_USER_TEMPLATE.format(
        max_clips=max_clips,
        segments_json=segments_json
    )
    
    return SHORTLIST_SYSTEM, user


def format_refine_prompt(clips: list) -> tuple[str, str]:
    """
    Format the refine prompt with clip data.
    
    Args:
        clips: List of clip data with text
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    import json
    
    clips_json = json.dumps([
        {
            "start_sec": c["start_sec"],
            "end_sec": c["end_sec"],
            "text": c.get("text", "")[:1500],
            "risk_flags": c.get("risk_flags", []),
            "keywords": c.get("keywords", [])
        }
        for c in clips
    ], ensure_ascii=False, indent=2)
    
    user = REFINE_USER_TEMPLATE.format(clips_json=clips_json)
    
    return REFINE_SYSTEM, user
