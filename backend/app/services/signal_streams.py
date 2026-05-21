"""
Signal Streams — Auto-ingestion from 3 signal sources.

Source 1: Social Media (Twitter) — manual inject via dashboard (existing)
Source 2: Rescue 1122 Call Feed — auto-generates alerts from call spike patterns
Source 3: LESCO Grid Sensors — auto-generates alerts from power grid anomalies

All sources feed into the same pipeline. The Observer handles credibility
scoring differently based on source type.
"""

import asyncio
import json
import random
import uuid
from pathlib import Path
from typing import Optional

from app.utils.timezone import now_pkt_iso


# ═══════════════════════════════════════════════════════════════
# MOCK DATA TEMPLATES — Rescue 1122 & LESCO alerts
# ═══════════════════════════════════════════════════════════════

RESCUE_1122_ALERTS = [
    {
        "area": "Walled City",
        "neighborhood": "walled_city",
        "type": "heatstroke",
        "template": "Rescue 1122 Alert: {calls} heatstroke calls received from {area} in last 30 minutes. {details}",
        "details_pool": [
            "Multiple elderly patients reported unconscious near Mochi Gate.",
            "Field team reports crowd gathering at Shahi Hammam, several people fainted.",
            "Ambulance AMB-003 requesting backup — 3 critical patients at Delhi Gate.",
        ],
        "call_range": (8, 25),
    },
    {
        "area": "Liberty Market",
        "neighborhood": "gulberg_iii",
        "type": "accident",
        "template": "Rescue 1122 Dispatch Log: Multi-vehicle accident reported at {area}. {details}",
        "details_pool": [
            "3 vehicles involved, 5 injuries reported. Traffic blocked on MM Alam Road.",
            "Motorcycle-rickshaw collision, 2 critical. Ambulance dispatched.",
            "Hit-and-run near Liberty roundabout, pedestrian critical. Police notified.",
        ],
        "call_range": (3, 8),
    },
    {
        "area": "DHA Phase 5",
        "neighborhood": "dha_phase_5",
        "type": "power_outage",
        "template": "Rescue 1122 Alert: {calls} calls from {area} — residents trapped in elevators during power outage. {details}",
        "details_pool": [
            "3 elevators stuck in commercial plaza, 12 people trapped.",
            "Elderly woman on ventilator — power backup failed. Critical case.",
            "Traffic signals down on Khayaban-e-Iqbal, minor accidents reported.",
        ],
        "call_range": (5, 15),
    },
    {
        "area": "Model Town",
        "neighborhood": "model_town",
        "type": "flood",
        "template": "Rescue 1122 Alert: {calls} calls from {area} — water logging and flooding reported. {details}",
        "details_pool": [
            "Canal Road flooded, vehicles stranded. Rescue boats requested.",
            "Basement flooding in Model Town Link Road, families evacuating.",
            "Sewage overflow near Model Town Park, health hazard alert.",
        ],
        "call_range": (4, 12),
    },
]

LESCO_SENSOR_ALERTS = [
    {
        "area": "DHA Phase 5",
        "neighborhood": "dha_phase_5",
        "type": "power_outage",
        "template": "LESCO Grid Alert: {area} — {details}",
        "details_pool": [
            "Complete grid failure on Feeder DHA-7. Load exceeded 142% of rated capacity. 25,000 consumers affected. ETA restoration: 4-6 hours.",
            "Transformer overload at DHA Phase 5 grid station. Temperature: 98°C (critical threshold: 85°C). Emergency shutdown initiated.",
            "Cascading trip: DHA-5, DHA-6, DHA-7 feeders offline. 45MW load shed. Priority restoration for hospitals in progress.",
        ],
    },
    {
        "area": "Walled City",
        "neighborhood": "walled_city",
        "type": "power_outage",
        "template": "LESCO Grid Alert: {area} — {details}",
        "details_pool": [
            "Feeder WC-3 tripped at 14:35 PKT. 15,000 consumers without power. Peak demand period — AC load causing grid stress.",
            "Underground cable fault detected between Bhati Gate and Delhi Gate substations. Repair crew dispatched. No ETA.",
            "Load shedding enforced on Walled City feeders WC-1 through WC-4. Duration: 2 hours. Heat index: 52°C.",
        ],
    },
    {
        "area": "Gulberg III",
        "neighborhood": "gulberg_iii",
        "type": "power_outage",
        "template": "LESCO Grid Alert: {area} — {details}",
        "details_pool": [
            "Voltage fluctuation alert on Gulberg-Main feeder. Voltage dropped to 168V (nominal: 220V). Industrial consumers at risk.",
            "Scheduled maintenance on Gulberg-III 132kV grid station cancelled due to emergency load. Overload warning issued.",
        ],
    },
    {
        "area": "Shahdara",
        "neighborhood": "shahdara",
        "type": "flood",
        "template": "LESCO Grid Alert: {area} — {details}",
        "details_pool": [
            "Water ingress detected at Shahdara substation. Safety shutdown of 3 feeders serving 18,000 consumers. Flood risk to equipment.",
            "Ground fault relay triggered at Shahdara-2 feeder. Cause: waterlogging near transformer. Power cut to 8,000 consumers as precaution.",
        ],
    },
]


class SignalStreamManager:
    """Manages auto-ingestion from multiple signal sources."""

    def __init__(self, db, ws_manager):
        self.db = db
        self.ws_manager = ws_manager
        self._tasks = {}  # stream_name -> asyncio.Task
        self._active = {}  # stream_name -> bool
        self._stats = {
            "twitter": {"signals_generated": 0, "active": False},
            "rescue_1122": {"signals_generated": 0, "active": False},
            "lesco_sensors": {"signals_generated": 0, "active": False},
        }

    @property
    def status(self) -> dict:
        return {
            name: {
                "active": self._active.get(name, False),
                "signals_generated": self._stats[name]["signals_generated"],
            }
            for name in self._stats
        }

    async def start_stream(self, stream_name: str, interval_seconds: int = 20) -> dict:
        """Start an auto-ingestion stream."""
        if stream_name not in self._stats:
            return {"error": f"Unknown stream: {stream_name}"}

        if self._active.get(stream_name):
            return {"status": "already_running", "stream": stream_name}

        self._active[stream_name] = True
        self._stats[stream_name]["active"] = True

        if stream_name == "rescue_1122":
            self._tasks[stream_name] = asyncio.create_task(
                self._run_rescue_stream(interval_seconds)
            )
        elif stream_name == "lesco_sensors":
            self._tasks[stream_name] = asyncio.create_task(
                self._run_lesco_stream(interval_seconds)
            )

        # Broadcast stream status
        await self.ws_manager.broadcast_trace({
            "event": "stream_started",
            "stream": stream_name,
            "interval_seconds": interval_seconds,
            "timestamp": now_pkt_iso(),
        })

        return {"status": "started", "stream": stream_name, "interval": interval_seconds}

    async def stop_stream(self, stream_name: str) -> dict:
        """Stop an auto-ingestion stream."""
        if stream_name not in self._stats:
            return {"error": f"Unknown stream: {stream_name}"}

        self._active[stream_name] = False
        self._stats[stream_name]["active"] = False

        if stream_name in self._tasks:
            self._tasks[stream_name].cancel()
            del self._tasks[stream_name]

        await self.ws_manager.broadcast_trace({
            "event": "stream_stopped",
            "stream": stream_name,
            "timestamp": now_pkt_iso(),
        })

        return {"status": "stopped", "stream": stream_name}

    async def stop_all(self):
        """Stop all streams."""
        for name in list(self._active.keys()):
            await self.stop_stream(name)

    # ─────────────────────────────────────────────────
    # Rescue 1122 Stream
    # ─────────────────────────────────────────────────

    async def _run_rescue_stream(self, interval: int):
        """Generate periodic Rescue 1122 call spike alerts."""
        try:
            while self._active.get("rescue_1122"):
                alert = random.choice(RESCUE_1122_ALERTS)
                calls = random.randint(*alert["call_range"])
                details = random.choice(alert["details_pool"])
                text = alert["template"].format(
                    calls=calls, area=alert["area"], details=details
                )

                signal_id = f"r1122_{uuid.uuid4().hex[:8]}"
                raw_signal = {
                    "id": signal_id,
                    "user": "Rescue_1122_Official",
                    "follower_count": 500000,
                    "verified": True,
                    "text": text,
                    "timestamp": now_pkt_iso(),
                    "geo_hint": alert["area"],
                    "source": "rescue_1122",
                    "source_credibility": 0.95,
                }

                # Broadcast that a new signal arrived from this source
                await self.ws_manager.broadcast_alert({
                    "event": "signal_ingested",
                    "source": "rescue_1122",
                    "signal_id": signal_id,
                    "text_preview": text[:100],
                    "area": alert["area"],
                    "timestamp": now_pkt_iso(),
                })

                # Process through pipeline
                from app.agents.orchestrator import run_pipeline
                await run_pipeline(raw_signal, self.db, self.ws_manager)

                self._stats["rescue_1122"]["signals_generated"] += 1

                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            pass

    # ─────────────────────────────────────────────────
    # LESCO Sensor Stream
    # ─────────────────────────────────────────────────

    async def _run_lesco_stream(self, interval: int):
        """Generate periodic LESCO grid sensor anomaly alerts."""
        try:
            while self._active.get("lesco_sensors"):
                alert = random.choice(LESCO_SENSOR_ALERTS)
                details = random.choice(alert["details_pool"])
                text = alert["template"].format(
                    area=alert["area"], details=details
                )

                signal_id = f"lesco_{uuid.uuid4().hex[:8]}"
                raw_signal = {
                    "id": signal_id,
                    "user": "LESCO_Grid_Monitor",
                    "follower_count": 0,
                    "verified": True,
                    "text": text,
                    "timestamp": now_pkt_iso(),
                    "geo_hint": alert["area"],
                    "source": "lesco_sensors",
                    "source_credibility": 0.98,
                }

                await self.ws_manager.broadcast_alert({
                    "event": "signal_ingested",
                    "source": "lesco_sensors",
                    "signal_id": signal_id,
                    "text_preview": text[:100],
                    "area": alert["area"],
                    "timestamp": now_pkt_iso(),
                })

                from app.agents.orchestrator import run_pipeline
                await run_pipeline(raw_signal, self.db, self.ws_manager)

                self._stats["lesco_sensors"]["signals_generated"] += 1

                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            pass
