"""
Deduplicator tool — detects duplicate/similar signals within a time+geo window.
Called by Observer Agent.
"""

import json
from datetime import datetime

# In-memory signal cache for deduplication
_recent_signals: list[dict] = []
MAX_CACHE = 200


def deduplicate_signal(
    signal_id: str,
    text: str,
    geo_hint: str,
    timestamp: str,
) -> str:
    """Check if a signal is a duplicate of a recently seen signal.
    Returns JSON with is_duplicate flag and matched_signal_id if duplicate.
    
    Args:
        signal_id: Unique ID of the signal to check
        text: Raw text content
        geo_hint: Location hint
        timestamp: ISO timestamp
    """
    try:
        global _recent_signals

        text_lower = text.lower().strip()
        geo_lower = (geo_hint or "").lower()

        for cached in _recent_signals:
            # Same location + similar text within 30 min = duplicate
            text_similarity = _simple_similarity(text_lower, cached["text"])
            geo_match = geo_lower and geo_lower in cached.get("geo", "")

            # Enforce 30-minute time window
            time_match = True
            try:
                cached_ts = datetime.fromisoformat(cached["timestamp"].replace("Z", "+00:00"))
                current_ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                time_diff_min = abs((current_ts - cached_ts).total_seconds()) / 60
                time_match = time_diff_min <= 30
            except Exception:
                time_match = True  # If timestamps can't be parsed, skip time check

            if text_similarity > 0.7 and geo_match and time_match:
                return json.dumps({
                    "is_duplicate": True,
                    "matched_signal_id": cached["id"],
                    "similarity": round(text_similarity, 2),
                    "action": "merge_into_existing_cluster",
                })

        # Not a duplicate — add to cache
        _recent_signals.append({
            "id": signal_id,
            "text": text_lower,
            "geo": geo_lower,
            "timestamp": timestamp,
        })
        if len(_recent_signals) > MAX_CACHE:
            _recent_signals = _recent_signals[-MAX_CACHE:]

        return json.dumps({"is_duplicate": False})
    except Exception as e:
        return json.dumps({"error": "DEDUP_FAILURE", "details": str(e)})


def _simple_similarity(a: str, b: str) -> float:
    """Simple word overlap similarity."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    overlap = words_a & words_b
    return len(overlap) / max(len(words_a), len(words_b))


def reset_dedup_cache():
    """Reset cache (called on simulation reset)."""
    global _recent_signals
    _recent_signals = []
