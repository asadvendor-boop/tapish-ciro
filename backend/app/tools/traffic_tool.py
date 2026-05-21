"""
Traffic tool — fetches traffic congestion data for Lahore roads.
LIVE mode: calls Google Routes API (computeRoutes) for real-time traffic.
DEMO mode: reads mock/traffic.json for controlled demo scenarios.
Called by Analyst Agent and Strategist Agent.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.utils.freshness import freshness_meta as _freshness_meta

MOCK_DIR = Path(__file__).resolve().parent.parent / "mock"

# ═══════════════════════════════════════════════════════════════
# LAHORE ROAD SEGMENTS — origin/destination coordinates
# Each defines a real road segment in Lahore with start/end points
# used for Google Routes API queries.
# ═══════════════════════════════════════════════════════════════

LAHORE_ROAD_SEGMENTS = [
    {
        "road": "GT Road (Shahdara to Data Darbar)",
        "segment": "shahdara_to_badami_bagh",
        "origin": {"latitude": 31.5895, "longitude": 74.3080},   # Shahdara
        "destination": {"latitude": 31.5710, "longitude": 74.3185},  # Badami Bagh
        "baseline_speed_kmh": 45,
        "neighborhoods": ["shahdara", "badami_bagh"],
    },
    {
        "road": "GT Road (Data Darbar to Mall Road)",
        "segment": "data_darbar_to_mall",
        "origin": {"latitude": 31.5710, "longitude": 74.3185},   # Data Darbar
        "destination": {"latitude": 31.5580, "longitude": 74.3240},  # Railway Station
        "baseline_speed_kmh": 40,
        "neighborhoods": ["walled_city", "data_darbar", "railway_station"],
    },
    {
        "road": "Mall Road",
        "segment": "mall_road_full",
        "origin": {"latitude": 31.5580, "longitude": 74.3240},   # GPO
        "destination": {"latitude": 31.5415, "longitude": 74.3440},  # Shimla Hill
        "baseline_speed_kmh": 50,
        "neighborhoods": ["mall_road", "shimla_hill", "gpo"],
    },
    {
        "road": "Ferozepur Road",
        "segment": "ferozepur_full",
        "origin": {"latitude": 31.5520, "longitude": 74.3290},   # Kalma Chowk
        "destination": {"latitude": 31.4680, "longitude": 74.2300},  # Thokar Niaz Baig
        "baseline_speed_kmh": 50,
        "neighborhoods": ["kalma_chowk", "ichhra", "model_town", "thokar"],
    },
    {
        "road": "Canal Road",
        "segment": "canal_full",
        "origin": {"latitude": 31.5200, "longitude": 74.3530},   # Thokar side
        "destination": {"latitude": 31.4750, "longitude": 74.3630},  # DHA side
        "baseline_speed_kmh": 60,
        "neighborhoods": ["canal_road", "model_town", "dha"],
    },
    {
        "road": "Multan Road",
        "segment": "multan_road",
        "origin": {"latitude": 31.5200, "longitude": 74.3490},   # Chauburji
        "destination": {"latitude": 31.4500, "longitude": 74.3000},  # Chungi
        "baseline_speed_kmh": 50,
        "neighborhoods": ["chauburji", "samanabad", "multan_road"],
    },
    {
        "road": "Jail Road",
        "segment": "jail_road",
        "origin": {"latitude": 31.5350, "longitude": 74.3500},   # Shimla Hill
        "destination": {"latitude": 31.5140, "longitude": 74.3190},  # Ichra
        "baseline_speed_kmh": 50,
        "neighborhoods": ["jail_road", "gulberg", "ichra"],
    },
    {
        "road": "Walled City Inner Streets",
        "segment": "walled_city_inner",
        "origin": {"latitude": 31.5850, "longitude": 74.3120},   # Bhati Gate
        "destination": {"latitude": 31.5790, "longitude": 74.3220},  # Delhi Gate
        "baseline_speed_kmh": 15,
        "neighborhoods": ["walled_city", "bhati_gate", "delhi_gate", "mochi_gate"],
    },
    {
        "road": "Misri Shah Road",
        "segment": "misri_shah",
        "origin": {"latitude": 31.5770, "longitude": 74.3050},   # Misri Shah
        "destination": {"latitude": 31.5700, "longitude": 74.3150},  # Badami Bagh
        "baseline_speed_kmh": 35,
        "neighborhoods": ["misri_shah", "badami_bagh"],
    },
    {
        "road": "MM Alam Road",
        "segment": "mm_alam_road",
        "origin": {"latitude": 31.5210, "longitude": 74.3480},   # Liberty
        "destination": {"latitude": 31.5120, "longitude": 74.3430},  # Hussain Chowk
        "baseline_speed_kmh": 40,
        "neighborhoods": ["gulberg_iii", "liberty", "mm_alam"],
    },
]

# Static fallback for when all APIs fail
_TRAFFIC_FALLBACK = {
    "source": "static_fallback",
    "roads": [
        {"road": "GT Road", "segment": "Walled City", "congestion_index": 0.8, "avg_speed_kmh": 12, "incidents": ["heavy congestion"]},
        {"road": "Mall Road", "segment": "GPO to Shimla Hill", "congestion_index": 0.6, "avg_speed_kmh": 20, "incidents": []},
    ],
    "fallback_note": "Traffic data unavailable. Using peak-hour historical estimates with reduced confidence.",
}


# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def get_traffic_data(area: str) -> str:
    """Get current traffic congestion levels for roads near a given area.
    Returns congestion index, average speed, and any incidents.
    In LIVE mode, fetches real-time traffic from Google Routes API.
    In DEMO mode, reads from mock/traffic.json.

    Args:
        area: The area or road name to check traffic for (e.g. 'walled_city', 'GT Road', 'Mall Road')
    """
    from app.services.data_mode import is_live

    if is_live():
        return _get_live_traffic(area)
    else:
        return _get_mock_traffic(area)


# ═══════════════════════════════════════════════════════════════
# LIVE MODE — Google Routes API
# ═══════════════════════════════════════════════════════════════

def _classify_congestion(ratio: float) -> str:
    """Classify congestion from duration/staticDuration ratio."""
    if ratio >= 2.5:
        return "severe"
    elif ratio >= 1.8:
        return "heavy"
    elif ratio >= 1.3:
        return "moderate"
    else:
        return "light"


def _compute_route(origin: dict, destination: dict, api_key: str) -> dict:
    """Call Google Routes API computeRoutes for a single road segment."""
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    payload = json.dumps({
        "origin": {"location": {"latLng": origin}},
        "destination": {"location": {"latLng": destination}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Goog-Api-Key", api_key)
    req.add_header("X-Goog-FieldMask", "routes.duration,routes.staticDuration,routes.distanceMeters")

    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _parse_duration(duration_str: str) -> int:
    """Parse '1320s' -> 1320 (seconds)."""
    if not duration_str:
        return 0
    return int(duration_str.rstrip("s"))


def _get_live_traffic(area: str) -> str:
    """Fetch real-time traffic from Google Routes API for relevant Lahore roads."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return json.dumps({
            "error": "GOOGLE_MAPS_API_KEY not configured",
            **_TRAFFIC_FALLBACK,
        })

    area_lower = area.lower().replace(" ", "_").replace("-", "_")
    now_iso = datetime.now(timezone(timedelta(hours=5))).isoformat()

    # Find relevant road segments for the requested area
    relevant_segments = []
    for seg in LAHORE_ROAD_SEGMENTS:
        # Match by neighborhood, road name, or segment name
        seg_matches = (
            area_lower in seg["segment"]
            or area_lower in seg["road"].lower()
            or any(area_lower in n for n in seg["neighborhoods"])
            or any(n in area_lower for n in seg["neighborhoods"])
        )
        if seg_matches:
            relevant_segments.append(seg)

    # If no specific match, query the top 5 most critical roads
    if not relevant_segments:
        relevant_segments = LAHORE_ROAD_SEGMENTS[:5]

    roads = []
    errors = []

    for seg in relevant_segments:
        try:
            result = _compute_route(seg["origin"], seg["destination"], api_key)

            if "routes" not in result or not result["routes"]:
                errors.append(f"{seg['road']}: No route found")
                continue

            route = result["routes"][0]
            duration_s = _parse_duration(route.get("duration", "0s"))
            static_duration_s = _parse_duration(route.get("staticDuration", "0s"))
            distance_m = route.get("distanceMeters", 0)

            # Compute congestion metrics
            if static_duration_s > 0:
                congestion_ratio = duration_s / static_duration_s
                congestion_index = min(1.0, round((congestion_ratio - 1.0) / 2.0, 2))
                congestion_index = max(0.0, congestion_index)
            else:
                congestion_ratio = 1.0
                congestion_index = 0.0

            # Estimate average speed from distance and duration
            if duration_s > 0:
                avg_speed_kmh = round((distance_m / 1000) / (duration_s / 3600), 1)
            else:
                avg_speed_kmh = seg["baseline_speed_kmh"]

            # Determine incidents from congestion severity
            incidents = []
            congestion_level = _classify_congestion(congestion_ratio)
            if congestion_level == "severe":
                incidents.append("traffic_jam")
            elif congestion_level == "heavy":
                incidents.append("heavy_congestion")

            roads.append({
                "road": seg["road"],
                "segment": seg["segment"],
                "congestion_level": congestion_level,
                "congestion_index": round(congestion_index, 2),
                "congestion_ratio": round(congestion_ratio, 2),
                "avg_speed_kmh": avg_speed_kmh,
                "baseline_speed_kmh": seg["baseline_speed_kmh"],
                "duration_seconds": duration_s,
                "free_flow_seconds": static_duration_s,
                "distance_meters": distance_m,
                "incidents": incidents,
            })

        except Exception as e:
            errors.append(f"{seg['road']}: {str(e)[:100]}")
            # Add fallback entry for this road
            roads.append({
                "road": seg["road"],
                "segment": seg["segment"],
                "congestion_level": "unknown",
                "congestion_index": 0.5,
                "avg_speed_kmh": seg["baseline_speed_kmh"] * 0.6,
                "baseline_speed_kmh": seg["baseline_speed_kmh"],
                "incidents": ["data_unavailable"],
                "error": str(e)[:100],
            })

    result = {
        "source": "google_routes_api_live",
        "area": area,
        "timestamp": now_iso,
        "roads": roads,
        "segments_queried": len(relevant_segments),
        "segments_succeeded": len(roads) - len(errors),
        **_freshness_meta(now_iso),
    }

    if errors:
        result["api_errors"] = errors

    return json.dumps(result)


# ═══════════════════════════════════════════════════════════════
# DEMO MODE — Mock JSON
# ═══════════════════════════════════════════════════════════════

def _get_mock_traffic(area: str) -> str:
    """Original mock data path — reads from mock/traffic.json."""
    try:
        with open(MOCK_DIR / "traffic.json") as f:
            data = json.load(f)

        area_lower = area.lower()
        matching_roads = []

        for road in data.get("roads", []):
            road_name_lower = road["road"].lower()
            segment_lower = road["segment"].lower()
            if area_lower in road_name_lower or area_lower in segment_lower or road_name_lower in area_lower:
                matching_roads.append(road)

        if not matching_roads:
            matching_roads = data.get("roads", [])

        return json.dumps({
            "source": "mock_data",
            "area": area,
            "timestamp": data.get("timestamp"),
            "roads": matching_roads,
            "scenario_6_data": data.get("scenario_6_congestion_spike"),
            **_freshness_meta(data.get("timestamp")),
        })
    except Exception as e:
        return json.dumps({"error": "TRAFFIC_FETCH_FAILURE", "details": str(e), **_TRAFFIC_FALLBACK})
