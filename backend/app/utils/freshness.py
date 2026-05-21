"""
Shared data freshness utility — computes age metadata from source timestamps.
Used by sensor, weather, and traffic tools to detect stale data.
"""

from datetime import datetime, timezone, timedelta

_STALE_THRESHOLD_SECONDS = 7200  # 2 hours
_PKT = timezone(timedelta(hours=5))


def freshness_meta(timestamp_str: str | None) -> dict:
    """Compute data freshness metadata from a source timestamp.
    
    Returns dict with:
        data_freshness: "fresh" | "stale" | "unknown"
        data_age_seconds: int or None
        source_timestamp: original timestamp string
        is_stale: bool
        staleness_note: warning string if stale, else None
    """
    if not timestamp_str:
        return {"data_freshness": "unknown", "data_age_seconds": None, "is_stale": True}
    try:
        now = datetime.now(_PKT)
        source_time = datetime.fromisoformat(timestamp_str)
        age = (now - source_time).total_seconds()
        is_stale = age > _STALE_THRESHOLD_SECONDS
        return {
            "data_freshness": "stale" if is_stale else "fresh",
            "data_age_seconds": int(age),
            "source_timestamp": timestamp_str,
            "is_stale": is_stale,
            "staleness_note": f"WARNING: Data is {int(age // 60)} minutes old. Reduce confidence." if is_stale else None,
        }
    except Exception:
        return {"data_freshness": "unknown", "data_age_seconds": None, "is_stale": True}
