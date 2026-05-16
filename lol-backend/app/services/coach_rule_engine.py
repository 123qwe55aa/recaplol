"""Deterministic coaching rules for fallback AI coach reports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _confidence(match_count: int) -> str:
    if match_count < 5:
        return "low"
    if match_count < 10:
        return "medium"
    return "high"


def score_context(context: dict) -> dict:
    """Rank up to three data-backed improvement priorities from context."""
    averages = context.get("averages") or {}
    role_profile = context.get("role_profile") or {}
    match_count = int(_number(context.get("match_count"), 0))
    primary_champions = context.get("primary_champions") or []
    findings = []

    deaths = _number(averages.get("deaths"))
    if deaths >= 6.0:
        findings.append(
            {
                "category": "deaths",
                "title": "Reduce avoidable deaths",
                "severity": round(min(1.0, deaths / 10.0), 2),
                "evidence": f"{deaths:.1f} average deaths across {match_count} matches.",
                "recommendation": "Review deaths before major objectives and reset sooner when waves are already handled.",
            }
        )

    cs_per_minute = _number(averages.get("cs_per_minute"))
    if role_profile.get("cs_is_primary", True) and 0 < cs_per_minute < 6.0:
        findings.append(
            {
                "category": "cs",
                "title": "Improve income consistency",
                "severity": round(min(0.95, (6.0 - cs_per_minute) / 3.0 + 0.35), 2),
                "evidence": f"{cs_per_minute:.1f} CS per minute in the recent sample.",
                "recommendation": "Set a 10-minute CS target and catch side waves before grouping.",
            }
        )

    vision_score = _number(averages.get("vision_score"))
    if vision_score < 18.0:
        findings.append(
            {
                "category": "vision",
                "title": "Raise vision impact",
                "severity": round(min(0.9, (18.0 - vision_score) / 18.0 + 0.35), 2),
                "evidence": f"{vision_score:.1f} average vision score across recent games.",
                "recommendation": "Refresh wards around objective timers and buy a control ward before contested fights.",
            }
        )

    if match_count >= 5 and len(primary_champions) <= 1:
        champion_name = (primary_champions[0] or {}).get("champion_name", "one champion")
        findings.append(
            {
                "category": "champion_pool",
                "title": "Add a reliable backup pick",
                "severity": 0.5,
                "evidence": f"Recent games are concentrated on {champion_name}.",
                "recommendation": "Keep your main pick, but practice one backup champion for draft flexibility.",
            }
        )

    findings.sort(key=lambda item: item["severity"], reverse=True)
    return {
        "confidence": _confidence(match_count),
        "findings": findings[:3],
    }


def build_fallback_report(context: dict, findings: list[dict]) -> dict:
    """Build a plain dict report payload from deterministic findings."""
    match_count = int(_number(context.get("match_count"), 0))
    confidence = _confidence(match_count)
    priorities = findings[:3]

    if priorities:
        top_titles = ", ".join(item["title"] for item in priorities)
        summary = f"Focus this block on: {top_titles}."
    else:
        summary = "Recent games do not show a single urgent weakness; keep reviewing fundamentals."

    return {
        "summary": summary,
        "confidence": confidence,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_window": {
            "match_count": match_count,
            "recent_match_ids": list(context.get("recent_match_ids") or []),
            "fingerprint": context.get("data_fingerprint"),
        },
        "priorities": priorities,
        "follow_up_questions": [
            "Which of these habits felt most noticeable in your recent games?",
            "Do you want drills for lane phase, mid game, or objective setup?",
        ],
    }
