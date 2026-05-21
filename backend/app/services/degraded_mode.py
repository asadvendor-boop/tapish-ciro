"""
Degraded Mode Controller — global state for simulating infrastructure failures.
Used by Scenario 5 (degraded_mode) to trigger stale data, rate limits, and tool errors
so judges can see the system gracefully degrade with fallbacks and reduced confidence.

Tools read from this module to decide whether to simulate failures.
The StreamSimulator activates/deactivates degraded conditions per scenario.
"""

from dataclasses import dataclass, field


@dataclass
class DegradedState:
    """Current degraded-mode simulation flags."""
    active: bool = False
    weather_api_stale: bool = False
    stale_minutes: int = 0
    simulate_rate_limit: bool = False
    rate_limit_countdown: int = 0  # first N Gemini calls will get simulated 429
    missing_geo_tweet: str = ""    # tweet ID that should have its geo stripped
    duplicate_tweets: list = field(default_factory=list)  # tweets to inject twice


# Singleton — tools import this directly
_state = DegradedState()


def activate(conditions: dict):
    """Activate degraded mode with given conditions from scenario JSON."""
    global _state
    _state = DegradedState(
        active=True,
        weather_api_stale=conditions.get("weather_api_stale", False),
        stale_minutes=conditions.get("stale_minutes", 45),
        simulate_rate_limit=conditions.get("simulate_rate_limit", False),
        rate_limit_countdown=2 if conditions.get("simulate_rate_limit") else 0,
        missing_geo_tweet=conditions.get("missing_geo_tweet", ""),
        duplicate_tweets=conditions.get("duplicate_tweets", []),
    )


def deactivate():
    """Reset to normal mode."""
    global _state
    _state = DegradedState()


def is_active() -> bool:
    return _state.active


def should_stale_weather() -> bool:
    return _state.active and _state.weather_api_stale


def stale_minutes() -> int:
    return _state.stale_minutes if _state.active else 0


def should_simulate_rate_limit() -> bool:
    """Returns True if the next Gemini call should get a simulated 429.
    Decrements the counter so only the first N calls fail (then retry succeeds).
    """
    if _state.active and _state.rate_limit_countdown > 0:
        _state.rate_limit_countdown -= 1
        return True
    return False


def should_strip_geo(tweet_id: str) -> bool:
    return _state.active and tweet_id == _state.missing_geo_tweet


def get_duplicate_tweet_ids() -> list:
    return _state.duplicate_tweets if _state.active else []
