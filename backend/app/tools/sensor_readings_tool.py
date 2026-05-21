"""
Sensor readings tool — fetches environmental + grid sensor data.
LIVE mode: calls OpenAQ API (free, no key) for real Lahore AQI/PM2.5
         + Google Air Quality API for hyper-local data.
DEMO mode: reads mock/sensors.json for controlled scenarios.
Called by Analyst and Auditor Agents.
"""

import json
import os
from pathlib import Path

from app.utils.freshness import freshness_meta as _freshness_meta

MOCK_DIR = Path(__file__).resolve().parent.parent / "mock"

# Lahore coordinates
LAHORE_LAT = 31.5497
LAHORE_LNG = 74.3436

# Static fallback when sensor data is completely unavailable
_SENSOR_FALLBACK = {
    "source": "static_fallback",
    "grid": {"voltage_v": 210, "load_pct": 85, "status": "stressed", "transformer_temp_c": 72},
    "grid_analysis": "FALLBACK: Estimated stressed grid based on historical May average.",
}


def _fetch_openaq() -> dict:
    """Fetch real-time air quality from OpenAQ for Lahore (free, no API key)."""
    import urllib.request

    # OpenAQ v3: search for locations near Lahore
    url = (
        f"https://api.openaq.org/v3/locations"
        f"?coordinates={LAHORE_LAT},{LAHORE_LNG}"
        f"&radius=25000"
        f"&limit=5"
        f"&order_by=distance"
    )

    req = urllib.request.Request(url, headers={
        "User-Agent": "Tapish/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode())


def _fetch_google_aqi(lat: float, lng: float) -> dict:
    """Fetch air quality from Google Air Quality API (uses existing Maps key)."""
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return {"error": "No Google Maps API key configured"}

    url = "https://airquality.googleapis.com/v1/currentConditions:lookup"
    payload = json.dumps({
        "location": {"latitude": lat, "longitude": lng},
        "extraComputations": ["HEALTH_RECOMMENDATIONS", "DOMINANT_POLLUTANT_CONCENTRATION"],
    }).encode()

    req = urllib.request.Request(
        f"{url}?key={api_key}",
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Tapish/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode())


def _classify_aqi(aqi: int) -> str:
    if aqi > 300: return "hazardous"
    if aqi > 200: return "very_unhealthy"
    if aqi > 150: return "unhealthy"
    if aqi > 100: return "unhealthy_sensitive"
    if aqi > 50: return "moderate"
    return "good"


def get_sensor_readings(neighborhood: str) -> str:
    """Get environmental sensor data for a Lahore neighborhood.
    LIVE: Real AQI from OpenAQ + Google Air Quality API.
    DEMO: Mock LESCO grid + temperature sensor data.

    Args:
        neighborhood: The neighborhood to check (e.g. 'walled_city', 'misri_shah')
    """
    from app.services.data_mode import is_live

    if is_live():
        return _get_live_sensors(neighborhood)
    else:
        return _get_mock_sensors(neighborhood)


def _get_live_sensors(neighborhood: str) -> str:
    """Fetch real air quality data from OpenAQ + Google AQI."""
    from datetime import datetime
    neighborhood_key = neighborhood.lower().replace(" ", "_").replace("-", "_")

    result = {
        "source": "live_apis",
        "neighborhood": neighborhood_key,
        "timestamp": datetime.now().isoformat(),
    }

    # --- OpenAQ ---
    try:
        openaq_data = _fetch_openaq()
        locations = openaq_data.get("results", [])

        if locations:
            # Aggregate latest readings from nearest stations
            pm25_values = []
            pm10_values = []
            station_names = []

            for loc in locations[:3]:  # top 3 nearest
                station_names.append(loc.get("name", "Unknown"))
                for sensor in loc.get("sensors", []):
                    param = sensor.get("parameter", {}).get("name", "")
                    latest = sensor.get("latest", {})
                    value = latest.get("value")
                    if value is not None:
                        if "pm25" in param.lower() or "pm2.5" in param.lower():
                            pm25_values.append(value)
                        elif "pm10" in param.lower():
                            pm10_values.append(value)

            avg_pm25 = round(sum(pm25_values) / len(pm25_values), 1) if pm25_values else None
            avg_pm10 = round(sum(pm10_values) / len(pm10_values), 1) if pm10_values else None

            # Estimate AQI from PM2.5 (US EPA breakpoints simplified)
            estimated_aqi = None
            if avg_pm25 is not None:
                if avg_pm25 <= 12: estimated_aqi = int(avg_pm25 * 50 / 12)
                elif avg_pm25 <= 35.4: estimated_aqi = int(50 + (avg_pm25 - 12) * 50 / 23.4)
                elif avg_pm25 <= 55.4: estimated_aqi = int(100 + (avg_pm25 - 35.4) * 50 / 20)
                elif avg_pm25 <= 150.4: estimated_aqi = int(150 + (avg_pm25 - 55.4) * 50 / 95)
                elif avg_pm25 <= 250.4: estimated_aqi = int(200 + (avg_pm25 - 150.4) * 100 / 100)
                else: estimated_aqi = int(300 + (avg_pm25 - 250.4) * 100 / 150)

            result["air_quality"] = {
                "source": "openaq",
                "stations_used": station_names,
                "pm25_ug_m3": avg_pm25,
                "pm10_ug_m3": avg_pm10,
                "estimated_aqi": estimated_aqi,
                "aqi_category": _classify_aqi(estimated_aqi) if estimated_aqi else "unknown",
            }
        else:
            result["air_quality"] = {"source": "openaq", "note": "No stations found near Lahore"}

    except Exception as e:
        result["air_quality"] = {"source": "openaq", "error": str(e)}

    # --- Google Air Quality API ---
    try:
        google_data = _fetch_google_aqi(LAHORE_LAT, LAHORE_LNG)

        if "indexes" in google_data:
            idx = google_data["indexes"][0] if google_data["indexes"] else {}
            result["google_aqi"] = {
                "source": "google_air_quality_api",
                "aqi": idx.get("aqi"),
                "category": idx.get("category", ""),
                "dominant_pollutant": idx.get("dominantPollutant", ""),
                "color": idx.get("color", {}),
            }

            # Health recommendations
            recs = google_data.get("healthRecommendations", {})
            if recs:
                result["google_aqi"]["health_recommendations"] = {
                    "general": recs.get("generalPopulation", ""),
                    "elderly": recs.get("elderly", ""),
                    "children": recs.get("children", ""),
                    "athletes": recs.get("athletes", ""),
                }

            # Pollutant details
            pollutants = google_data.get("pollutants", [])
            if pollutants:
                result["google_aqi"]["pollutants"] = {
                    p["code"]: {
                        "display_name": p.get("displayName", ""),
                        "concentration_ug_m3": p.get("concentration", {}).get("value"),
                    }
                    for p in pollutants[:5]
                }
        elif "error" in google_data:
            result["google_aqi"] = {"source": "google", "error": google_data["error"]}

    except Exception as e:
        result["google_aqi"] = {"source": "google", "error": str(e)}

    # --- Grid data stays mock (LESCO has no API) ---
    try:
        with open(MOCK_DIR / "sensors.json") as f:
            mock_data = json.load(f)
        grid_data = mock_data.get("grid_zones", {}).get(neighborhood_key)
        if not grid_data:
            for key in mock_data.get("grid_zones", {}):
                if neighborhood_key in key or key in neighborhood_key:
                    grid_data = mock_data["grid_zones"][key]
                    break
        if grid_data:
            result["grid"] = grid_data
            result["grid_analysis"] = _analyze_grid(grid_data)
            result["grid_note"] = "LESCO grid data from mock (no public API available)"
    except Exception:
        result["grid_note"] = "Grid data unavailable"

    result.update(_freshness_meta(result["timestamp"]))
    return json.dumps(result)


def _get_mock_sensors(neighborhood: str) -> str:
    """Original mock data path."""
    try:
        with open(MOCK_DIR / "sensors.json") as f:
            data = json.load(f)

        neighborhood_key = neighborhood.lower().replace(" ", "_").replace("-", "_")

        grid_data = data.get("grid_zones", {}).get(neighborhood_key)
        if not grid_data:
            for key in data.get("grid_zones", {}):
                if neighborhood_key in key or key in neighborhood_key:
                    grid_data = data["grid_zones"][key]
                    neighborhood_key = key
                    break

        temp_sensors = {}
        for sensor_key, sensor_data in data.get("temperature_sensors", {}).items():
            if neighborhood_key in sensor_key:
                temp_sensors[sensor_key] = sensor_data

        if not grid_data and not temp_sensors:
            return json.dumps({"error": f"No sensor data for '{neighborhood}'", "available_zones": list(data.get("grid_zones", {}).keys())})

        result = {
            "source": "mock_data",
            "neighborhood": neighborhood_key,
            "timestamp": data.get("timestamp"),
            **_freshness_meta(data.get("timestamp")),
        }
        if grid_data:
            result["grid"] = grid_data
            result["grid_analysis"] = _analyze_grid(grid_data)
        if temp_sensors:
            result["temperature_sensors"] = temp_sensors

        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": "SENSOR_FETCH_FAILURE", "details": str(e),
                           "fallback_note": "Sensor network unreachable. Use last-known readings with reduced confidence.",
                           **_SENSOR_FALLBACK})


def _analyze_grid(grid: dict) -> str:
    """Interpret grid data for agent reasoning."""
    status = grid.get("status", "unknown")
    voltage = grid.get("voltage_v", 0)
    load = grid.get("load_pct", 0)

    if status == "outage":
        return f"COMPLETE OUTAGE. Voltage at {voltage}V. No power. Outage since {grid.get('last_outage', 'unknown')}."
    elif status == "critical_drop":
        return f"CRITICAL VOLTAGE DROP. {voltage}V (nominal 220V). Load at {load}%. Transformer at {grid.get('transformer_temp_c')}°C. Imminent failure risk."
    elif status == "stressed":
        return f"GRID STRESSED. {voltage}V. Load {load}%. Transformer at {grid.get('transformer_temp_c')}°C. Monitor closely."
    else:
        return f"Grid normal. {voltage}V. Load {load}%."
