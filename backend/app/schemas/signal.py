"""Signal schema — output of the Observer Agent."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    """Geographic coordinate with optional label."""
    lat: float
    lng: float
    label: str | None = None


class Signal(BaseModel):
    """
    A single ingested signal from any source.
    Created by the Observer Agent after credibility scoring and intent extraction.
    """
    id: str
    source: Literal["twitter", "weather", "traffic", "sensor", "call", "field_report"]
    raw_content: str
    language: Literal["urdu", "roman_urdu", "english", "n/a"] = "n/a"
    timestamp: datetime
    geolocation: GeoPoint | None = None
    geo_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Credibility (computed as mean of credibility_factors)
    credibility_score: float = Field(default=0.0, ge=0.0, le=1.0)
    credibility_factors: dict = Field(default_factory=lambda: {
        "specificity_score": 0.0,
        "emotional_amplification": 0.0,
        "viral_intent_score": 0.0,
        "source_authority": 0.0,
    })

    # Urgency
    urgency_keywords: list[str] = Field(default_factory=list)
    urgency_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Velocity and contradictions
    mention_velocity: int = Field(default=0, description="Mentions per 5 min window")
    contradictions: list[str] = Field(default_factory=list, description="IDs of contradicting signals")

    # Extracted intent (from Observer's Gemini call)
    extracted_intent: dict = Field(default_factory=lambda: {
        "crisis_type_hint": "none",
        "location_mentions": [],
        "severity_hint": "low",
        "translation_en": "",
        "trace_reasoning": "",
    })

    # Processing metadata
    processed: bool = False
    cluster_id: str | None = None
