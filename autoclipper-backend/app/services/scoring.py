"""
Scoring Service
Heuristic scoring + LLM score fusion + diversity filter.
Optimized for podcast/education/finance/motivation content (ID/EN mixed).
"""
from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

# =============================================================================
# Hook Markers - Tuned for Indonesian/English podcast/edu/finance/motivation
# =============================================================================

HOOK_MARKERS_ID = [
    "ternyata", "faktanya", "yang orang gak tau", "yang banyak orang",
    "ini salah", "salah kaprah", "masalahnya", "bahaya", "jangan",
    "kuncinya", "cara paling", "cara terbaik", "yang bikin",
    "yang kamu gak sadar", "ini penting", "rahasia", "trik",
    "sebenarnya", "padahal", "banyak yang salah"
]

HOOK_MARKERS_EN = [
    "here's the truth", "most people", "the problem is", "this is why",
    "you're doing it wrong", "the secret", "what nobody tells you",
    "let me be clear", "the real reason", "here's what", "actually",
    "the truth is", "you need to know", "stop doing this"
]

# Finance/investing markers
FIN_MARKERS = [
    "roi", "return", "inflasi", "interest", "bunga", "compound",
    "risk", "diversify", "volatility", "margin", "leverage",
    "cashflow", "net worth", "yield", "cagr", "valuation",
    "liquidity", "drawdown", "saham", "investasi", "reksadana",
    "crypto", "bitcoin", "portfolio", "dividen"
]

# Actionable content patterns
ACTION_PATTERNS = [
    r"\b(3|tiga|5|lima|7|tujuh|10)\s+(hal|cara|langkah|tips|step)\b",
    r"\b(cara|how to|steps?|tips?)\b",
    r"\b(lakukan|stop|mulai|catat|hindari|coba|ingat|harus)\b",
    r"\b(first|second|third|pertama|kedua|ketiga)\b"
]

# Payoff/conclusion markers
PAYOFF_MARKERS_ID = [
    "jadi intinya", "makanya", "kesimpulannya", "intinya",
    "poinnya adalah", "yang penting", "takeaway"
]

PAYOFF_MARKERS_EN = [
    "so the point is", "that's why", "in summary", "the takeaway is",
    "bottom line", "in conclusion", "the key is"
]

# Risk penalty values
RISK_PENALTY = {
    "needs_context": 10,
    "too_slow": 10,
    "sensitive": 15,
    "unclear_audio": 10,
    "copyright_music": 8,
}


def _norm01(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def hook_score(text: str) -> float:
    """
    Score based on hook markers in first ~25 words.
    Higher score = stronger hook potential.
    """
    t = text.lower()
    early = " ".join(t.split()[:25])
    
    score = 0.0
    
    for m in HOOK_MARKERS_ID:
        if m in early:
            score += 12.0
    for m in HOOK_MARKERS_EN:
        if m in early:
            score += 12.0
            
    # Punctuation excitement
    score += min(10.0, 2.0 * early.count("!"))
    score += min(8.0, 1.5 * early.count("?"))
    
    return min(100.0, score)


def finance_score(text: str) -> float:
    """
    Score for finance/investing content.
    """
    t = text.lower()
    score = 0.0
    
    # Numeric signals (percentages, numbers)
    score += min(20.0, 5.0 * len(re.findall(r"\b\d+(\.\d+)?%?\b", t)))
    
    for m in FIN_MARKERS:
        if m in t:
            score += 8.0
            
    return min(100.0, score)


def action_score(text: str) -> float:
    """
    Score for actionable/how-to content.
    """
    t = text.lower()
    score = 0.0
    
    for pat in ACTION_PATTERNS:
        if re.search(pat, t):
            score += 20.0
            
    return min(100.0, score)


def payoff_score(text: str) -> float:
    """
    Score based on conclusion/payoff markers near end.
    """
    t = text.lower()
    tail = " ".join(t.split()[-35:])
    
    score = 0.0
    
    for m in PAYOFF_MARKERS_ID:
        if m in tail:
            score += 25.0
    for m in PAYOFF_MARKERS_EN:
        if m in tail:
            score += 25.0
            
    return min(100.0, score)


def clarity_score(text: str) -> float:
    """
    Penalize vague references, reward concrete nouns.
    """
    t = text.lower()
    
    # Vague references (needs context)
    vague_count = sum(t.count(x) for x in [
        "itu", "ini", "yang tadi", "gitu", "that", "it", "they", "those"
    ])
    
    # Concrete content (long words as proxy)
    words = t.split()
    long_words = sum(1 for w in words if len(w) >= 7)
    
    raw = 60.0 + 2.0 * long_words - 6.0 * vague_count
    return max(0.0, min(100.0, raw))


def pacing_score(word_count: int, duration_sec: float) -> float:
    """
    Score based on speaking pace (words per minute).
    Optimal: 130-190 WPM for short-form.
    """
    if duration_sec <= 0:
        return 0.0
        
    wpm = (word_count / duration_sec) * 60.0
    
    if wpm < 80:
        return 10.0  # Too slow
    if wpm > 240:
        return 10.0  # Too fast
        
    # Bell curve around 160 WPM
    center = 160.0
    dist = abs(wpm - center)
    return max(20.0, min(100.0, 100.0 - (dist / 80.0) * 80.0))


def compute_final_score(
    llm_score: float,
    text: str,
    risk_flags: List[str],
    duration_sec: float,
) -> Dict[str, float]:
    """
    Compute final clip score using weighted formula:
    
    S_final = 0.50*S_llm + 0.18*S_hook + 0.10*S_fin + 
              0.08*S_action + 0.08*S_payoff + 0.04*S_clarity + 
              0.02*S_pacing - risk_penalty
    """
    wc = len(text.split())
    
    s_hook = hook_score(text)
    s_fin = finance_score(text)
    s_action = action_score(text)
    s_payoff = payoff_score(text)
    s_clarity = clarity_score(text)
    s_pacing = pacing_score(wc, duration_sec)

    penalty = sum(RISK_PENALTY.get(f, 0) for f in risk_flags)

    final = (
        0.50 * llm_score
        + 0.18 * s_hook
        + 0.10 * s_fin
        + 0.08 * s_action
        + 0.08 * s_payoff
        + 0.04 * s_clarity
        + 0.02 * s_pacing
        - penalty
    )
    
    final = max(0.0, min(100.0, final))
    
    return {
        "final_score": final,
        "llm_score": llm_score,
        "hook_score": s_hook,
        "finance_score": s_fin,
        "action_score": s_action,
        "payoff_score": s_payoff,
        "clarity_score": s_clarity,
        "pacing_score": s_pacing,
        "risk_penalty": float(penalty),
    }


def jaccard_similarity(a: Set[str], b: Set[str]) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def diversity_filter(
    items: List[Tuple[str, float, List[str]]],
    threshold: float = 0.7,
) -> List[str]:
    """
    Filter clips to ensure diversity by keyword similarity.
    Keep higher scored clips when similarity exceeds threshold.
    
    Args:
        items: List of (clip_id, score, keywords)
        threshold: Jaccard similarity threshold (default 0.7)
        
    Returns:
        List of kept clip_ids
    """
    kept: List[Tuple[str, float, Set[str]]] = []
    
    # Sort by score descending
    sorted_items = sorted(items, key=lambda x: x[1], reverse=True)
    
    for clip_id, score, kws in sorted_items:
        kwset = set(k.lower().strip() for k in kws if k and k.strip())
        
        # Check similarity with already kept clips
        is_diverse = True
        for _, _, existing_kws in kept:
            if jaccard_similarity(kwset, existing_kws) >= threshold:
                is_diverse = False
                break
                
        if is_diverse:
            kept.append((clip_id, score, kwset))
            
    return [k[0] for k in kept]
