"""Resource and ResourceAllocation schemas — used by the Strategist Agent."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .signal import GeoPoint


class Resource(BaseModel):
    """A single deployable resource unit (ambulance, generator, tanker, etc.)."""
    id: str
    type: Literal["ambulance", "generator", "water_tanker", "rescue_team", "drone", "field_team"]
    operator: Literal["rescue_1122", "lesco", "wasa", "edhi", "chhipa", "punjab_health"]
    current_location: GeoPoint
    status: Literal["available", "dispatched", "in_use", "returning"] = "available"
    capacity: int = 1
    assigned_crisis: str | None = None


class ResourceAllocation(BaseModel):
    """
    Strategist Agent's allocation decision for a single crisis.
    Includes explicit trade-off justification (the rubric's 'trade-off moment').
    """
    crisis_id: str
    allocated: list[str] = Field(
        default_factory=list,
        description="Resource IDs allocated to this crisis"
    )
    rationale: str = Field(
        default="",
        description="Natural language justification from Strategist"
    )
    tradeoffs: list[dict] = Field(
        default_factory=list,
        description="[{deprioritized_crisis_id, reason}] — crises NOT prioritized and why"
    )
    expected_response_time_minutes: float = 0.0
    mortality_risk_reduction_estimate: Literal["low", "medium", "high"] = "low"
    trace_reasoning: str = ""
