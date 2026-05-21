"""
Timezone utilities for TAPISH — all timestamps in PKT (Pakistan Standard Time, UTC+5).
"""

from datetime import datetime, timezone, timedelta

PKT = timezone(timedelta(hours=5))


def now_pkt() -> datetime:
    """Return current time in PKT timezone."""
    return datetime.now(PKT)


def now_pkt_iso() -> str:
    """Return current PKT time as ISO 8601 string with timezone offset."""
    return datetime.now(PKT).isoformat()
