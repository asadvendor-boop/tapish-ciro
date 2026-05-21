"""
Forecast Tool — Weather forecast for Lahore.
Returns hourly predictions with heat risk assessment.
"""

import json
import math
from datetime import datetime, timedelta, timezone
from google.adk.tools import FunctionTool

# Pakistan Standard Time (UTC+5)
_PKT = timezone(timedelta(hours=5))


def get_weather_forecast(hours_ahead: int = 24) -> str:
    """Get weather forecast for Lahore for the next N hours.

    Args:
        hours_ahead: Number of hours to forecast (max 48).

    Returns:
        dict with hourly forecasts and risk assessment.
    """
    hours_ahead = min(hours_ahead, 48)
    now = datetime.now(_PKT)

    # Realistic Lahore May heatwave pattern
    # Peak: 14:00 (47°C), Low: 02:00 (32°C)
    base = 39.5  # May average
    amplitude = 7.5  # swing ±7.5°C
    hourly = []
    high_risk_hours = []

    for h in range(hours_ahead):
        forecast_time = now + timedelta(hours=h)
        hour = forecast_time.hour

        # Smooth 24hr sinusoidal: peak ~14:00 (47°C), trough ~02:00 (32°C)
        temp = base + amplitude * math.sin(2 * math.pi * (hour - 5) / 24)

        # Humidity inverse to temperature
        humidity = max(15, 65 - int(temp - 32))

        # Heat index (simplified)
        heat_index = temp + (humidity * 0.1)

        # Risk level
        if temp >= 45:
            risk = "extreme"
        elif temp >= 42:
            risk = "very_high"
        elif temp >= 39:
            risk = "high"
        elif temp >= 36:
            risk = "moderate"
        else:
            risk = "low"

        entry = {
            "time": forecast_time.strftime("%Y-%m-%d %H:%M"),
            "hour": hour,
            "temperature_c": round(temp, 1),
            "humidity_pct": humidity,
            "heat_index": round(heat_index, 1),
            "risk_level": risk,
            "uv_index": min(12, max(0, 11 - abs(hour - 13))) if 6 <= hour <= 20 else 0,
        }
        hourly.append(entry)

        if risk in ("extreme", "very_high"):
            high_risk_hours.append(entry)

    # Peak
    peak = max(hourly, key=lambda x: x["temperature_c"])

    return json.dumps({
        "city": "Lahore",
        "forecast_generated": now.isoformat(),
        "hours_ahead": hours_ahead,
        "peak_temperature": peak["temperature_c"],
        "peak_time": peak["time"],
        "peak_risk": peak["risk_level"],
        "high_risk_hours": len(high_risk_hours),
        "high_risk_windows": high_risk_hours[:8],  # cap for context length
        "preposition_recommended": len(high_risk_hours) >= 3,
        "hourly": hourly[:12],  # first 12 hours for context
        "advisory": (
            f"EXTREME HEAT WARNING: Peak of {peak['temperature_c']}°C expected at {peak['time']}. "
            f"{len(high_risk_hours)} hours of very high / extreme risk. "
            "Pre-position ambulances and water tankers in high-vulnerability neighborhoods."
            if len(high_risk_hours) >= 3
            else f"Moderate heat expected. Peak {peak['temperature_c']}°C at {peak['time']}."
        ),
    })


forecast_tool = FunctionTool(func=get_weather_forecast)
