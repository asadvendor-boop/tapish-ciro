"""
Data mode toggle — LIVE vs DEMO.
In LIVE mode, tools call real external APIs (Open-Meteo, OpenAQ, Google AQI).
In DEMO mode, tools read from mock/ JSON files for controlled demo scenarios.
Toggle via env var DATA_MODE or runtime API call.
"""

import os

_data_mode: str = os.getenv("DATA_MODE", "demo")  # default to demo for safety


def get_mode() -> str:
    return _data_mode


def set_mode(mode: str) -> str:
    global _data_mode
    mode = mode.lower().strip()
    if mode not in ("live", "demo"):
        raise ValueError("DATA_MODE must be 'live' or 'demo'")
    _data_mode = mode
    return _data_mode


def is_live() -> bool:
    return _data_mode == "live"
