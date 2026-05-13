"""Frequency analysis and rule-based clutter suggestions."""
from datetime import datetime
from typing import Any, Dict, Optional

from tracker import ClutterTracker


def compute_stats(
    tracker: ClutterTracker, room: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """Enrich raw DB stats with frequency ratio and days-since-last-seen."""
    raw = tracker.get_object_stats(room)
    now = datetime.now()

    stats: Dict[str, Dict[str, Any]] = {}
    for label, info in raw.items():
        total = info["total_sessions"]
        frequency = info["sessions_seen"] / total if total > 0 else 0.0

        try:
            last_seen = datetime.fromisoformat(info["last_seen"])
            days_since = (now - last_seen).total_seconds() / 86400
        except Exception:
            days_since = 999.0

        stats[label] = {
            **info,
            "frequency": round(frequency, 3),
            "days_since_last_seen": round(days_since, 1),
        }

    return stats


def simple_suggestions(stats: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Build decluttering suggestions from object frequency and recency."""
    keep, donate, review = [], [], []

    for label, info in stats.items():
        if info["frequency"] >= 0.6 or info["days_since_last_seen"] <= 7:
            keep.append({"item": label, "reason": "Frequently present or recently seen"})
        elif info["frequency"] <= 0.2 and info["days_since_last_seen"] >= 30:
            donate.append({"item": label, "reason": "Rarely present and not seen recently"})
        else:
            review.append({"item": label, "reason": "Moderate usage - review manually"})

    return {
        "keep": keep,
        "donate": donate,
        "layout": [],
        "review": review,
        "summary": (
            f"Rule-based analysis: {len(keep)} items to keep, "
            f"{len(donate)} candidates for removal, {len(review)} to review."
        ),
    }
