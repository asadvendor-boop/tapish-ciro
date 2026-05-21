"""Action schema — output of the Operator Agent."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .signal import GeoPoint


class Action(BaseModel):
    """
    A concrete action executed by the Operator Agent.
    Each action tracks expected impact, resource cost, and side effects.
    """
    id: str
    type: Literal[
        "reroute_traffic", "dispatch_unit", "open_cooling_center",
        "alert_hospital", "request_grid_priority", "deploy_water_tanker",
        "issue_public_alert", "mosque_announcement"
    ]
    crisis_id: str = ""
    target_location: GeoPoint | None = None
    parameters: dict = Field(default_factory=dict)

    # Impact prediction (before/after simulation for rubric)
    expected_impact: dict = Field(default_factory=lambda: {
        "response_time_delta": "",
        "lives_saved_est": 0,
        "congestion_delta": "",
    })

    # Resource cost transparency
    resource_cost: dict = Field(default_factory=lambda: {
        "units_consumed": 0,
        "estimated_hours": 0,
        "opportunity_cost": "",
    })

    # Side effects (the rubric demands side-effect prediction)
    side_effects: list[str] = Field(
        default_factory=list,
        description="e.g. 'hospital alert may cause panic rush on GT Road'"
    )

    # Status lifecycle
    status: Literal["planned", "executing", "completed", "failed", "cancelled"] = "planned"
