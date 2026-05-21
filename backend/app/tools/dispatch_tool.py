import json
import os
from datetime import datetime
from pathlib import Path

import firebase_admin
from firebase_admin import firestore

MOCK_DIR = Path(__file__).resolve().parent.parent / "mock"


def _get_db():
    """Get Firestore client. firebase_admin is initialized by main.py/database.py."""
    try:
        return firestore.client()
    except Exception:
        return None


def _now_iso():
    from datetime import timezone, timedelta as td
    pkt = timezone(td(hours=5))
    return datetime.now(pkt).isoformat()


def dispatch_resource(resource_id: str, crisis_id: str, destination: str) -> str:
    """Dispatch a resource unit to a crisis location. Updates resource status to 'dispatched' in Firestore.
    
    Args:
        resource_id: ID of the resource to dispatch (e.g. 'amb_001')
        crisis_id: ID of the crisis event this dispatch is for
        destination: Target location name for the dispatch
    """
    try:
        db = _get_db()
        db_updated = False
        if db:
            doc_ref = db.collection("resources").document(resource_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_ref.update({
                    "status": "dispatched",
                    "assigned_crisis": crisis_id,
                    "status_history": firestore.ArrayUnion([{
                        "status": "dispatched",
                        "timestamp": _now_iso(),
                        "destination": destination,
                    }]),
                })
                db_updated = True

        return json.dumps({
            "status": "dispatched",
            "resource_id": resource_id,
            "crisis_id": crisis_id,
            "destination": destination,
            "db_updated": db_updated,
            "note": f"Resource {resource_id} dispatched to {destination} for crisis {crisis_id}.",
        })
    except Exception as e:
        return json.dumps({"error": "DISPATCH_FAILURE", "details": str(e)})


def get_available_resources(resource_type: str = "all") -> str:
    """Get list of available (non-dispatched) resources from Firestore, optionally filtered by type.
    
    Args:
        resource_type: Filter by type ('ambulance', 'generator', 'water_tanker', 'rescue_team', or 'all')
    """
    try:
        db = _get_db()
        all_resources = []

        if db:
            resources_ref = db.collection("resources")
            if resource_type != "all":
                from google.cloud.firestore_v1 import FieldFilter
                query = resources_ref.where(filter=FieldFilter("type", "==", resource_type))
            else:
                query = resources_ref
            docs = query.get()
            for doc in docs:
                d = doc.to_dict()
                # Serialize current_location for JSON compatibility
                if isinstance(d.get("current_location"), dict):
                    d["current_location"] = json.dumps(d["current_location"])
                all_resources.append(d)

        if all_resources:
            available = [r for r in all_resources if r.get("status") == "available"]
            return json.dumps({
                "total": len(all_resources),
                "available": len(available),
                "dispatched": len([r for r in all_resources if r.get("status") == "dispatched"]),
                "resource_type": resource_type,
                "resources": available,
            })
        
        # Fallback: static JSON
        with open(MOCK_DIR / "resources.json") as f:
            resources = json.load(f)
        
        if resource_type != "all":
            resources = [r for r in resources if r["type"] == resource_type]
        
        available = [r for r in resources if r.get("status") == "available"]
        
        return json.dumps({
            "total": len(resources),
            "available": len(available),
            "resource_type": resource_type,
            "resources": available,
            "source": "static_fallback",
        })
    except Exception as e:
        return json.dumps({"error": "RESOURCE_FETCH_FAILURE", "details": str(e)})


def get_hospital_capacity(area: str = "all") -> str:
    """Get hospital bed capacity and occupancy for hospitals near a given area.
    
    Args:
        area: Area name to find nearby hospitals (or 'all' for all hospitals)
    """
    try:
        with open(MOCK_DIR / "hospitals.json") as f:
            hospitals = json.load(f)
        
        if area != "all":
            area_lower = area.lower()
            nearby = [
                h for h in hospitals
                if area_lower in h["name"].lower()
                or area_lower in h.get("neighborhood", "").lower()
                or area_lower in h.get("area", "").lower()
            ]
            hospitals = nearby if nearby else hospitals
        
        return json.dumps({
            "area": area,
            "hospitals": hospitals,
            "total_emergency_beds": sum(h["emergency_beds"] for h in hospitals),
            "total_heatstroke_beds": sum(h["heatstroke_beds"] for h in hospitals),
        })
    except Exception as e:
        return json.dumps({"error": "HOSPITAL_FETCH_FAILURE", "details": str(e)})


def estimate_travel_time(from_location: str, to_location: str) -> str:
    """Estimate travel time between two locations considering current traffic.
    
    Args:
        from_location: Starting location name
        to_location: Destination location name
    """
    try:
        from app.tools.geocode_tool import LAHORE_LOCATIONS
        from app.services.allocator import haversine_km, estimate_travel_time_minutes
        
        from_lower = from_location.lower()
        to_lower = to_location.lower()
        
        from_coords = None
        to_coords = None
        
        for key, coords in LAHORE_LOCATIONS.items():
            if not from_coords and (key == from_lower or key in from_lower or from_lower in key):
                from_coords = coords
            if not to_coords and (key == to_lower or key in to_lower or to_lower in key):
                to_coords = coords
            if from_coords and to_coords:
                break
        
        if not from_coords or not to_coords:
            return json.dumps({"error": "Could not resolve one or both locations", "from": from_location, "to": to_location})
        
        distance = haversine_km(from_coords["lat"], from_coords["lng"], to_coords["lat"], to_coords["lng"])
        time_normal = estimate_travel_time_minutes(distance, 0.3)
        time_congested = estimate_travel_time_minutes(distance, 0.7)
        
        return json.dumps({
            "from": from_location,
            "to": to_location,
            "distance_km": round(distance, 1),
            "travel_time_normal_min": round(time_normal, 1),
            "travel_time_congested_min": round(time_congested, 1),
        })
    except Exception as e:
        return json.dumps({"error": "TRAVEL_TIME_FAILURE", "details": str(e)})
