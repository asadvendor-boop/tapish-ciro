"""
Recent signals tool — queries Firestore for nearby signals within a time/geo window.
Called by Analyst Agent for signal clustering.
Uses neighborhood_id for efficient Firestore exact-match queries.
"""

import json
from datetime import datetime, timedelta


# Map common location names to their neighborhood_id (from geocode_tool.py)
LOCATION_TO_NEIGHBORHOOD = {
    "bhati gate": "walled_city", "mochi gate": "walled_city", "shahalmi": "walled_city",
    "lohari gate": "walled_city", "walled city": "walled_city", "androon lahore": "walled_city",
    "data darbar": "walled_city", "anarkali": "walled_city",
    "misri shah": "misri_shah",
    "dha": "dha_phase_5", "dha phase 5": "dha_phase_5",
    "gulberg": "gulberg_iii", "gulberg iii": "gulberg_iii", "liberty market": "gulberg_iii",
    "model town": "model_town", "johar town": "model_town",
    "cantt": "cantt", "mall road": "cantt", "mayo hospital": "cantt",
    "shahdara": "shahdara", "gt road": "shahdara",
    "baghbanpura": "baghbanpura",
    "canal road": "gulberg_iii", "ferozepur road": "gulberg_iii",
}


def _resolve_neighborhood(location: str) -> str:
    """Resolve a location name to a neighborhood_id for Firestore query."""
    loc_lower = location.lower().strip()
    if not loc_lower:
        return ""
    # Direct match
    if loc_lower in LOCATION_TO_NEIGHBORHOOD:
        return LOCATION_TO_NEIGHBORHOOD[loc_lower]
    # Substring match
    for key, nid in LOCATION_TO_NEIGHBORHOOD.items():
        if key in loc_lower or loc_lower in key:
            return nid
    return loc_lower.replace(" ", "_")  # Fallback: normalize as-is


def get_recent_signals(location: str, minutes: int = 30) -> str:
    """Query recent signals from Firestore for a given location.
    Uses neighborhood_id for efficient exact-match Firestore queries.
    
    Args:
        location: Location name to search for in signal content
        minutes: Time window in minutes to look back (default: 30)
    """
    try:
        from firebase_admin import firestore
        from google.cloud.firestore_v1 import FieldFilter

        db = firestore.client()
        neighborhood_id = _resolve_neighborhood(location)
        from datetime import timezone, timedelta as td
        PKT = timezone(td(hours=5))
        cutoff = (datetime.now(PKT) - timedelta(minutes=abs(minutes))).isoformat()

        # Primary query: exact match on neighborhood_id (Firestore-optimized)
        query = db.collection("signals").where(
            filter=FieldFilter("neighborhood_id", "==", neighborhood_id)
        ).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(20)
        docs = query.get()

        signals = []
        for doc in docs:
            d = doc.to_dict()
            ts = d.get("timestamp", "")
            if ts and ts < cutoff:
                continue
            signals.append({
                "signal_id": d.get("id"),
                "text_preview": (d.get("raw_content") or "")[:120],
                "credibility_score": d.get("credibility_score", 0),
                "urgency_score": d.get("urgency_score", 0),
                "timestamp": d.get("timestamp"),
                "cluster_id": d.get("cluster_id"),
                "neighborhood_id": d.get("neighborhood_id"),
            })

        # Fallback: if no results from neighborhood_id query, try text search
        if not signals:
            location_lower = location.lower()
            fallback_query = db.collection("signals").order_by(
                "timestamp", direction=firestore.Query.DESCENDING
            ).limit(50)
            fallback_docs = fallback_query.get()

            for doc in fallback_docs:
                d = doc.to_dict()
                ts = d.get("timestamp", "")
                if ts and ts < cutoff:
                    continue
                raw = (d.get("raw_content") or "").lower()
                geo = str(d.get("geolocation") or "").lower()
                if location_lower not in raw and location_lower not in geo:
                    continue
                signals.append({
                    "signal_id": d.get("id"),
                    "text_preview": (d.get("raw_content") or "")[:120],
                    "credibility_score": d.get("credibility_score", 0),
                    "urgency_score": d.get("urgency_score", 0),
                    "timestamp": d.get("timestamp"),
                    "cluster_id": d.get("cluster_id"),
                    "neighborhood_id": d.get("neighborhood_id"),
                })
                if len(signals) >= 20:
                    break

        return json.dumps({
            "location": location,
            "neighborhood_id": neighborhood_id,
            "minutes": minutes,
            "count": len(signals),
            "signals": signals,
            "cluster_hint": f"Found {len(signals)} historical signals from {location} (neighborhood: {neighborhood_id}). If multiple low-confidence signals cluster here, this pattern should RAISE your overall confidence." if signals else f"No historical signals from {location} (neighborhood: {neighborhood_id}).",
        })
    except Exception as e:
        return json.dumps({"error": "RECENT_SIGNALS_FAILURE", "details": str(e)})


def get_rescue_call_data(area: str) -> str:
    """Get Rescue 1122 call frequency data for an area.
    Used by Analyst for severity estimation and Auditor for cross-referencing.
    
    Args:
        area: Area name to check call data for (e.g. 'walled_city', 'liberty_market')
    """
    try:
        from pathlib import Path
        MOCK_DIR = Path(__file__).resolve().parent.parent / "mock"
        with open(MOCK_DIR / "calls.json") as f:
            data = json.load(f)
        
        area_key = area.lower().replace(" ", "_").replace("-", "_")
        
        hourly = data.get("hourly_calls", {}).get(area_key)
        call_types = data.get("call_types", {}).get(area_key, {})
        
        if hourly is None:
            return json.dumps({
                "area": area_key,
                "calls_found": False,
                "total_calls_today": 0,
                "note": f"No call data for '{area}'. This could indicate a false alarm — no emergency calls from this area.",
            })
        
        return json.dumps({
            "area": area_key,
            "calls_found": True,
            "hourly_calls": hourly,
            "hours_labels": data.get("hours_labels", []),
            "total_calls_today": sum(hourly),
            "peak_hour_calls": max(hourly),
            "call_types": call_types,
            "trend": "rising" if len(hourly) >= 3 and hourly[-1] > hourly[-3] else ("rising" if len(hourly) >= 2 and hourly[-1] > hourly[-2] else "stable"),
        })
    except Exception as e:
        return json.dumps({"error": "RESCUE_CALLS_FAILURE", "details": str(e)})
