"""
Weather tool — fetches weather data for a Lahore neighborhood.
LIVE mode: calls Open-Meteo API (free, no key) for real Lahore weather.
DEMO mode: reads mock/weather.json for controlled scenarios.
Called by Analyst Agent.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta

from app.utils.freshness import freshness_meta as _freshness_meta

MOCK_DIR = Path(__file__).resolve().parent.parent / "mock"

# Lahore coordinates
LAHORE_LAT = 31.5497
LAHORE_LNG = 74.3436

# Static fallback for when weather data is unavailable
_WEATHER_FALLBACK = {
    "source": "static_fallback",
    "peak_temp_c": 45.0,
    "avg_humidity_pct": 22,
    "heat_island_bonus_c": 3.0,
    "tree_cover_pct": 5,
    "current_conditions": {"temp_c": 43, "humidity": 25, "heat_index": 48, "risk_level": "extreme"},
    "alerts": [{"type": "extreme_heat", "message": "Fallback alert: Assume extreme heat based on May historical."}],
    "overview": {"condition": "extreme_heat", "temp_c": 45},
    "fallback_note": "Weather data unavailable. Using historical May averages with reduced confidence.",
}

# Heat island bonus per neighborhood (dense old city areas get extra heat)
_HEAT_ISLAND = {
    "walled_city": 4.0, "bhati_gate": 3.5, "misri_shah": 3.0,
    "gulberg": 1.5, "gulberg_iii": 1.5, "dha_phase_5": 1.0,
    "model_town": 1.2, "johar_town": 1.5, "liberty_chowk": 2.0,
    "cantt": 1.0, "township": 1.8,
}


def _fetch_open_meteo() -> dict:
    """Fetch real-time weather from Open-Meteo (free, no API key)."""
    import urllib.request

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAHORE_LAT}&longitude={LAHORE_LNG}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code"
        f"&hourly=temperature_2m,relative_humidity_2m,apparent_temperature"
        f"&daily=temperature_2m_max,temperature_2m_min,apparent_temperature_max"
        f"&timezone=Asia/Karachi"
        f"&forecast_days=2"
    )

    req = urllib.request.Request(url, headers={"User-Agent": "Tapish/1.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode())


def _classify_risk(apparent_temp: float) -> str:
    if apparent_temp >= 50: return "extreme"
    if apparent_temp >= 45: return "very_high"
    if apparent_temp >= 42: return "high"
    if apparent_temp >= 38: return "moderate"
    return "low"


def _generate_alerts(current: dict, daily: dict) -> list:
    """Generate heatwave alerts from real data."""
    alerts = []
    temp = current.get("temperature_2m", 0)
    apparent = current.get("apparent_temperature", 0)

    if apparent >= 45:
        alerts.append({
            "type": "extreme_heat",
            "message": f"EXTREME HEAT ALERT: Feels like {apparent}°C in Lahore. Heatstroke risk critical.",
            "severity": "critical",
        })
    elif apparent >= 42:
        alerts.append({
            "type": "heat_advisory",
            "message": f"HEAT ADVISORY: Apparent temperature {apparent}°C. Limit outdoor exposure.",
            "severity": "high",
        })

    # Check if tomorrow is even hotter
    daily_max = daily.get("apparent_temperature_max", [])
    if len(daily_max) > 1 and daily_max[1] > apparent + 2:
        alerts.append({
            "type": "heat_escalation",
            "message": f"TOMORROW WORSE: Forecast apparent temp {daily_max[1]}°C — pre-position resources.",
            "severity": "high",
        })

    return alerts


def get_weather_data(neighborhood: str) -> str:
    """Get current weather conditions and forecasts for a Lahore neighborhood.
    Returns temperature, humidity, heat index, and active weather alerts.
    In LIVE mode, fetches real data from Open-Meteo API.
    In DEMO mode, reads from mock/weather.json.

    Args:
        neighborhood: The neighborhood ID (e.g. 'walled_city', 'gulberg_iii', 'dha_phase_5')
    """
    from app.services.data_mode import is_live

    if is_live():
        return _get_live_weather(neighborhood)
    else:
        return _get_mock_weather(neighborhood)


def _get_live_weather(neighborhood: str) -> str:
    """Fetch real weather from Open-Meteo and enrich with neighborhood context."""
    try:
        data = _fetch_open_meteo()
        current = data.get("current", {})
        hourly = data.get("hourly", {})
        daily = data.get("daily", {})

        neighborhood_key = neighborhood.lower().replace(" ", "_").replace("-", "_")
        heat_bonus = _HEAT_ISLAND.get(neighborhood_key, 2.0)

        temp = current.get("temperature_2m", 40)
        humidity = current.get("relative_humidity_2m", 30)
        apparent = current.get("apparent_temperature", temp)

        # Adjust for heat island effect
        local_apparent = apparent + heat_bonus

        risk_level = _classify_risk(local_apparent)
        alerts = _generate_alerts(current, daily)

        return json.dumps({
            "source": "open_meteo_live",
            "neighborhood": neighborhood_key,
            "peak_temp_c": round(max(daily.get("temperature_2m_max", [temp])[:1] or [temp]), 1),
            "avg_humidity_pct": humidity,
            "heat_island_bonus_c": heat_bonus,
            "tree_cover_pct": 5,  # static for now
            "current_conditions": {
                "temp_c": round(temp, 1),
                "humidity": humidity,
                "apparent_temp_c": round(apparent, 1),
                "local_apparent_c": round(local_apparent, 1),
                "heat_index": round(local_apparent, 1),
                "wind_speed_kmh": current.get("wind_speed_10m", 0),
                "risk_level": risk_level,
            },
            "alerts": alerts,
            "overview": {
                "condition": "extreme_heat" if temp >= 40 else "hot" if temp >= 35 else "warm",
                "temp_c": round(temp, 1),
                "date": datetime.now().strftime("%Y-%m-%d"),
            },
            "daily_forecast": {
                "today_max": daily.get("temperature_2m_max", [None])[0],
                "today_min": daily.get("temperature_2m_min", [None])[0],
                "tomorrow_max": daily.get("temperature_2m_max", [None, None])[1] if len(daily.get("temperature_2m_max", [])) > 1 else None,
            },
            **_freshness_meta(datetime.now().isoformat()),
        })
    except Exception as e:
        return json.dumps({
            "error": "LIVE_WEATHER_FETCH_FAILURE",
            "details": str(e),
            "fallback_note": "Open-Meteo API unreachable. Using static fallback.",
            **_WEATHER_FALLBACK,
        })


def _get_mock_weather(neighborhood: str) -> str:
    """Original mock data path — reads from mock/weather.json."""
    try:
        with open(MOCK_DIR / "weather.json") as f:
            data = json.load(f)

        neighborhood_key = neighborhood.lower().replace(" ", "_").replace("-", "_")
        neighborhood_data = data.get("neighborhoods", {}).get(neighborhood_key)

        if not neighborhood_data:
            for key in data.get("neighborhoods", {}):
                if neighborhood_key in key or key in neighborhood_key:
                    neighborhood_data = data["neighborhoods"][key]
                    neighborhood_key = key
                    break

        if not neighborhood_data:
            return json.dumps({"error": f"No weather data for '{neighborhood}'. Available: {list(data.get('neighborhoods', {}).keys())}"})

        hourly = data.get("hourly", [])
        current_hour = hourly[-1] if hourly else {}

        overview_date = data.get("lahore_overview", {}).get("date", "")
        hourly_time = current_hour.get("hour", "")
        if overview_date and hourly_time:
            ts = f"{overview_date}T{hourly_time}:00+05:00"
        else:
            ts = data.get("metadata", {}).get("generated_at")

        # Degraded mode: artificially age the timestamp
        from app.services import degraded_mode
        if degraded_mode.should_stale_weather() and ts:
            try:
                real_ts = datetime.fromisoformat(ts)
                stale_ts = real_ts - timedelta(minutes=degraded_mode.stale_minutes())
                ts = stale_ts.isoformat()
            except Exception:
                pass

        return json.dumps({
            "source": "mock_data",
            "neighborhood": neighborhood_key,
            "peak_temp_c": neighborhood_data["peak_temp_c"],
            "avg_humidity_pct": neighborhood_data["avg_humidity"],
            "heat_island_bonus_c": neighborhood_data["heat_island_bonus"],
            "tree_cover_pct": neighborhood_data["tree_cover_pct"],
            "current_conditions": current_hour,
            "alerts": data.get("alerts", []),
            "overview": data.get("lahore_overview", {}),
            **_freshness_meta(ts),
        })
    except Exception as e:
        return json.dumps({"error": "WEATHER_FETCH_FAILURE", "details": str(e), **_WEATHER_FALLBACK})
