"""
Geocode tool — resolves Lahore location names to coordinates.
Uses the same location DB as degraded_mode.py for consistency.
"""

import json


# Lahore location database with accurate coordinates
LAHORE_LOCATIONS = {
    "bhati gate": {"lat": 31.5780, "lng": 74.3180, "label": "Bhati Gate, Walled City", "neighborhood": "walled_city"},
    "mochi gate": {"lat": 31.5820, "lng": 74.3220, "label": "Mochi Gate, Walled City", "neighborhood": "walled_city"},
    "shahalmi": {"lat": 31.5760, "lng": 74.3250, "label": "Shahalmi Market, Walled City", "neighborhood": "walled_city"},
    "shahalmi market": {"lat": 31.5760, "lng": 74.3250, "label": "Shahalmi Market, Walled City", "neighborhood": "walled_city"},
    "lohari gate": {"lat": 31.5770, "lng": 74.3150, "label": "Lohari Gate, Walled City", "neighborhood": "walled_city"},
    "taxali gate": {"lat": 31.5790, "lng": 74.3160, "label": "Taxali Gate, Walled City", "neighborhood": "walled_city"},
    "yakki gate": {"lat": 31.5810, "lng": 74.3240, "label": "Yakki Gate, Walled City", "neighborhood": "walled_city"},
    "walled city": {"lat": 31.5800, "lng": 74.3200, "label": "Walled City", "neighborhood": "walled_city"},
    "androon lahore": {"lat": 31.5800, "lng": 74.3200, "label": "Androon Lahore (Walled City)", "neighborhood": "walled_city"},
    "androon sheher": {"lat": 31.5800, "lng": 74.3200, "label": "Androon Sheher (Walled City)", "neighborhood": "walled_city"},
    "data darbar": {"lat": 31.5700, "lng": 74.3150, "label": "Data Darbar", "neighborhood": "walled_city"},
    "misri shah": {"lat": 31.5700, "lng": 74.3200, "label": "Misri Shah", "neighborhood": "misri_shah"},
    "shahdara": {"lat": 31.5900, "lng": 74.3400, "label": "Shahdara", "neighborhood": "shahdara"},
    "baghbanpura": {"lat": 31.5850, "lng": 74.3500, "label": "Baghbanpura", "neighborhood": "baghbanpura"},
    "dha": {"lat": 31.4500, "lng": 74.4000, "label": "DHA", "neighborhood": "dha_phase_5"},
    "dha phase 5": {"lat": 31.4500, "lng": 74.4050, "label": "DHA Phase 5", "neighborhood": "dha_phase_5"},
    "gulberg": {"lat": 31.5100, "lng": 74.3500, "label": "Gulberg", "neighborhood": "gulberg_iii"},
    "gulberg iii": {"lat": 31.5100, "lng": 74.3550, "label": "Gulberg III", "neighborhood": "gulberg_iii"},
    "model town": {"lat": 31.4750, "lng": 74.3350, "label": "Model Town", "neighborhood": "model_town"},
    "cantt": {"lat": 31.5250, "lng": 74.3600, "label": "Cantt", "neighborhood": "cantt"},
    "liberty market": {"lat": 31.5150, "lng": 74.3450, "label": "Liberty Market", "neighborhood": "gulberg_iii"},
    "anarkali": {"lat": 31.5600, "lng": 74.3300, "label": "Anarkali", "neighborhood": "walled_city"},
    "gt road": {"lat": 31.5700, "lng": 74.3300, "label": "GT Road", "neighborhood": "shahdara"},
    "mall road": {"lat": 31.5500, "lng": 74.3400, "label": "Mall Road", "neighborhood": "cantt"},
    "mayo hospital": {"lat": 31.5204, "lng": 74.3587, "label": "Mayo Hospital", "neighborhood": "cantt"},
    "services hospital": {"lat": 31.5150, "lng": 74.3550, "label": "Services Hospital", "neighborhood": "gulberg_iii"},
    "canal road": {"lat": 31.5000, "lng": 74.3400, "label": "Canal Road", "neighborhood": "gulberg_iii"},
    "ferozepur road": {"lat": 31.4900, "lng": 74.3600, "label": "Ferozepur Road", "neighborhood": "gulberg_iii"},
    "johar town": {"lat": 31.4700, "lng": 74.3700, "label": "Johar Town", "neighborhood": "model_town"},
}


def geocode_location(text: str, geo_hint: str) -> str:
    """Resolve a location name to GPS coordinates from the Lahore location database.
    Returns JSON with lat, lng, label, neighborhood, and confidence.
    
    Args:
        text: The raw text that may contain location references
        geo_hint: Explicit geographic hint provided with the signal
    """
    try:
        search = (geo_hint + " " + text).lower() if geo_hint else text.lower()
        best_match = None
        best_key_len = 0

        for key, coords in LAHORE_LOCATIONS.items():
            if key in search and len(key) > best_key_len:
                best_match = coords
                best_key_len = len(key)

        if best_match:
            return json.dumps({
                "resolved": True,
                "lat": best_match["lat"],
                "lng": best_match["lng"],
                "label": best_match["label"],
                "neighborhood": best_match["neighborhood"],
                "confidence": 0.85,
            })

        return json.dumps({
            "resolved": False,
            "lat": 31.5500,
            "lng": 74.3500,
            "label": "Lahore (city-wide fallback)",
            "neighborhood": "unknown",
            "confidence": 0.1,
            "note": "No specific location found in text. Using Lahore center.",
        })
    except Exception as e:
        return json.dumps({"error": "GEOCODE_FAILURE", "details": str(e)})
