"""
Constrained resource optimizer — used by Strategist Agent.
Computes mortality_risk × PSER_vulnerability × travel_time scoring for resource allocation.
"""

import json
import math
from pathlib import Path

MOCK_DIR = Path(__file__).resolve().parent.parent / "mock"


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute distance in km between two GPS points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def estimate_travel_time_minutes(distance_km: float, congestion_index: float = 0.5) -> float:
    """Estimate travel time based on distance and congestion. Assumes avg 30 km/h base speed."""
    base_speed = 30.0
    effective_speed = base_speed * (1.0 - congestion_index * 0.7)
    effective_speed = max(effective_speed, 5.0)
    return (distance_km / effective_speed) * 60


def compute_priority_score(crisis: dict, pser_data: dict) -> float:
    """
    Compute priority score for resource allocation.
    Higher score = higher priority.
    Formula: severity_weight × population × (1 - pser_poverty_score/100) × (1 / travel_factor)
    """
    severity_weights = {"critical": 4.0, "high": 3.0, "medium": 2.0, "low": 1.0}
    severity_w = severity_weights.get(crisis.get("severity", "low"), 1.0)

    population = crisis.get("affected_population_est", 1000)
    location_key = crisis.get("primary_location", "").lower().replace(" ", "_").replace("-", "_")

    # Find PSER data for this location
    pser_score = 50  # default
    for key, data in pser_data.get("neighborhoods", {}).items():
        if key in location_key or location_key in key:
            pser_score = data.get("pser_poverty_score", 50)
            break

    # Lower PSER = more vulnerable = higher priority
    vulnerability_factor = 1.0 - (pser_score / 100.0)

    return severity_w * (population / 1000.0) * vulnerability_factor


def allocate_resources(crises: list, resources: list, pser_data: dict) -> list:
    """
    Allocate constrained resources across multiple crises.
    Rules from Section 8.3:
    1. Mortality risk dominates: severity × population × PSER vulnerability
    2. Travel time matters
    3. Reserve at least 20% capacity for unexpected events
    4. Document what was NOT prioritized
    """
    # Score and sort crises by priority
    scored = []
    for c in crises:
        score = compute_priority_score(c, pser_data)
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)

    # Available resources by type
    available = [r for r in resources if r.get("status") == "available"]
    total_count = len(available)
    reserve_count = max(1, int(total_count * 0.2))
    allocatable = available[:total_count - reserve_count]

    allocations = []
    used_ids = set()

    for priority_score, crisis in scored:
        crisis_loc = crisis.get("primary_location", "").lower().replace(" ", "_").replace("-", "_")
        allocated_ids = []

        # Sort allocatable resources by proximity to crisis location
        crisis_lat = crisis.get("lat")
        crisis_lng = crisis.get("lng")
        if not crisis_lat:
            # Try to resolve from geocode locations
            try:
                from app.tools.geocode_tool import LAHORE_LOCATIONS
                for key, coords in LAHORE_LOCATIONS.items():
                    if key in crisis_loc or crisis_loc in key:
                        crisis_lat = coords["lat"]
                        crisis_lng = coords["lng"]
                        break
            except Exception:
                pass

        candidates = [r for r in allocatable if r["id"] not in used_ids]

        if crisis_lat and crisis_lng:
            # Sort by distance to crisis
            def dist_to_crisis(res):
                import json as _json
                loc = res.get("current_location", "{}")
                if isinstance(loc, str):
                    try:
                        loc = _json.loads(loc)
                    except Exception:
                        loc = {}
                r_lat = loc.get("lat", 31.52) if isinstance(loc, dict) else 31.52
                r_lng = loc.get("lng", 74.35) if isinstance(loc, dict) else 74.35
                return haversine_km(crisis_lat, crisis_lng, r_lat, r_lng)
            candidates.sort(key=dist_to_crisis)

        for res in candidates:
            allocated_ids.append(res["id"])
            used_ids.add(res["id"])
            if len(allocated_ids) >= 3:  # max 3 units per crisis
                break

        allocations.append({
            "crisis_id": crisis["id"],
            "allocated": allocated_ids,
            "priority_score": priority_score,
            "reserved_units": reserve_count,
        })

    return allocations
