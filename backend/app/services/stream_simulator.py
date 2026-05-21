"""
Stream Simulator — pumps mock data streams (tweets, weather, etc.) into the pipeline.
Configurable speed. Supports all 7 stress-test scenarios.
"""

import json
import asyncio
from pathlib import Path
from typing import Optional

from app.services.ws_manager import ConnectionManager
from app.services import degraded_mode


class StreamSimulator:
    """Simulates multi-source signal streams for demo scenarios."""

    def __init__(self, mock_dir: Path, db, ws_manager: ConnectionManager):
        self.mock_dir = mock_dir
        self.db = db
        self.ws_manager = ws_manager
        self.status = "idle"
        self.current_scenario: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        self._paused = False

        # Load mock data
        self._tweets = self._load_json("tweets.json", fallback=[])
        self._scenarios = self._load_json("stress_scenarios.json").get("scenarios", [])

    def _load_json(self, filename: str, fallback=None):
        path = self.mock_dir / filename
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return fallback if fallback is not None else {}

    def _get_scenario(self, scenario_id: str) -> Optional[dict]:
        for s in self._scenarios:
            if s["id"] == scenario_id:
                return s
        return None

    def _get_tweet_by_id(self, tweet_id: str) -> Optional[dict]:
        for t in self._tweets:
            if t["id"] == tweet_id:
                return t
        return None

    async def start(self, scenario_id: str) -> dict:
        """Start a scenario simulation."""
        scenario = self._get_scenario(scenario_id)
        if not scenario:
            return {"error": f"Scenario {scenario_id} not found"}

        self.status = "running"
        self.current_scenario = scenario_id
        self._paused = False

        # Start async task
        self._task = asyncio.create_task(self._run_scenario(scenario))
        return {"status": "started", "scenario": scenario_id, "name": scenario.get("name")}

    async def _run_scenario(self, scenario: dict):
        """Run a scenario by injecting tweets with delays."""
        try:
            delay = scenario.get("inject_delay_seconds", 3)
            tweet_ids = scenario.get("tweet_ids", [])

            # Activate degraded mode if scenario declares it
            conditions = scenario.get("degraded_conditions")
            if conditions:
                degraded_mode.activate(conditions)
                await self.ws_manager.broadcast("trace", {
                    "agent": "system", "event": "degraded_mode_activated",
                    "content": f"Degraded conditions active: {list(conditions.keys())}",
                    "phase": "adapt",
                })

            # Duplicate tweets (stress test: dedup should catch these)
            dup_ids = degraded_mode.get_duplicate_tweet_ids()
            if dup_ids:
                tweet_ids = tweet_ids + dup_ids  # append dupes at end

            for tweet_id in tweet_ids:
                if self._paused:
                    while self._paused:
                        await asyncio.sleep(0.5)

                tweet = self._get_tweet_by_id(tweet_id)
                if not tweet:
                    continue

                # Strip geo for degraded mode test
                if degraded_mode.should_strip_geo(tweet_id):
                    tweet = {**tweet}  # shallow copy
                    tweet.pop("geo_hint", None)
                    tweet["_degraded_geo_stripped"] = True

                # Process through pipeline
                await self.process_single_signal(tweet)
                await asyncio.sleep(delay)

            # Handle follow-up tweets (for false-negative scenario)
            followup_delay = scenario.get("followup_delay_seconds")
            followup_ids = scenario.get("followup_tweet_ids", [])
            if followup_delay and followup_ids:
                await asyncio.sleep(followup_delay)
                for tweet_id in followup_ids:
                    tweet = self._get_tweet_by_id(tweet_id)
                    if tweet:
                        await self.process_single_signal(tweet)
                        await asyncio.sleep(1)

            self.status = "completed"
        except asyncio.CancelledError:
            self.status = "cancelled"
        except Exception as e:
            self.status = f"error: {str(e)}"
        finally:
            # Always deactivate degraded mode when scenario ends
            if degraded_mode.is_active():
                degraded_mode.deactivate()

    async def process_single_signal(self, raw_tweet: dict) -> dict:
        """
        Process a single signal through the full agent pipeline.
        This is called by both the simulator and the live inject endpoint.
        Returns the pipeline result.
        """
        # Import here to avoid circular imports
        from app.agents.orchestrator import run_pipeline

        result = await run_pipeline(raw_tweet, self.db, self.ws_manager)
        return result

    def pause(self):
        self._paused = True
        self.status = "paused"

    def resume(self):
        self._paused = False
        self.status = "running"

    async def reset(self):
        """Reset simulator state."""
        if self._task and not self._task.done():
            self._task.cancel()
        self.status = "idle"
        self.current_scenario = None
        self._paused = False
        # Clear dedup in-memory cache so re-runs don't get false duplicate matches
        from app.tools.deduplicator_tool import reset_dedup_cache
        reset_dedup_cache()
