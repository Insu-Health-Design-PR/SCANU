"""Typed contracts for Layer 5 multi-sensor fusion."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FusionInputContract:
    """Normalised fusion output consumed by Layer 6 state machine."""

    frame_number: int
    timestamp_ms: float
    radar_id: str
    fused_score: float
    confidence: float
    trigger_score: float
    anomaly_score: float
    source_mode: str = "provisional_l1_l2"
    evidence: dict[str, float] = field(default_factory=dict)
