"""محرك مطابقة أسماء الفنيين باستخدام RapidFuzz."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from database.data_cleaner import clean_text

AUTO_LINK_THRESHOLD = 0.90
REVIEW_THRESHOLD = 0.50

TITLE_PREFIXES = [
    "المهندس", "مهندس", "م.", "الفني", "فني",
    "الأستاذ", "أ.", "السيد", "eng.", "eng", "mr.", "mr",
]


@dataclass
class TechnicianMatchResult:
    resolved_name: str | None
    confidence: float
    is_known: bool
    needs_review: bool
    candidates: list[str]
    warning: str | None


def _strip_title_prefix(name: str) -> str:
    normalized = clean_text(name).lower()
    for prefix in TITLE_PREFIXES:
        p = clean_text(prefix).lower()
        if normalized == p:
            return ""
        if normalized.startswith(p + " "):
            return normalized[len(p):].strip()
    return normalized


def _weighted_score(raw: str, known: str) -> float:
    raw_n = _strip_title_prefix(raw)
    known_n = _strip_title_prefix(known)
    if not raw_n or not known_n:
        return 0.0
    if raw_n == known_n:
        return 1.0
    token_sort = fuzz.token_sort_ratio(raw_n, known_n) / 100.0
    token_set = fuzz.token_set_ratio(raw_n, known_n) / 100.0
    partial = fuzz.partial_ratio(raw_n, known_n) / 100.0
    ratio = fuzz.ratio(raw_n, known_n) / 100.0
    max_len = max(len(raw_n), len(known_n), 1)
    lev = 1.0 - (Levenshtein.distance(raw_n, known_n) / max_len)
    return (token_sort * 0.30) + (token_set * 0.25) + (partial * 0.20) + (ratio * 0.15) + (lev * 0.10)


def match_technician(
    raw_name: str,
    known_technicians: list[dict[str, Any]],
    auto_threshold: float = AUTO_LINK_THRESHOLD,
) -> TechnicianMatchResult:
    """مطابقة اسم فني مع حساب Confidence Score."""
    raw_name = clean_text(raw_name)
    if not raw_name:
        return TechnicianMatchResult(
            resolved_name=None,
            confidence=0.0,
            is_known=False,
            needs_review=True,
            candidates=[],
            warning="اسم الفني فارغ.",
        )

    best_name: str | None = None
    best_score = 0.0
    score_map: dict[str, float] = {}

    for tech in known_technicians:
        known = clean_text(tech.get("fullname") or "")
        if not known:
            continue
        score = _weighted_score(raw_name, known)
        score_map[known] = score
        if score > best_score:
            best_score = score
            best_name = known

    candidates = [
        name for name, score in sorted(score_map.items(), key=lambda x: x[1], reverse=True)
        if score >= REVIEW_THRESHOLD
    ][:5]

    if best_name and best_score >= auto_threshold:
        return TechnicianMatchResult(
            resolved_name=best_name,
            confidence=best_score,
            is_known=True,
            needs_review=False,
            candidates=candidates,
            warning=None,
        )

    if best_name and best_score >= REVIEW_THRESHOLD:
        return TechnicianMatchResult(
            resolved_name=best_name,
            confidence=best_score,
            is_known=True,
            needs_review=True,
            candidates=candidates,
            warning=f"تطابق جزئي ({best_score:.0%}) — يحتاج مراجعة: \"{raw_name}\" → \"{best_name}\".",
        )

    return TechnicianMatchResult(
        resolved_name=None,
        confidence=best_score,
        is_known=False,
        needs_review=True,
        candidates=candidates,
        warning=f"لم يُعثر على فني مطابق لـ \"{raw_name}\".",
    )
