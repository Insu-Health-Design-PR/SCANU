"""Sensor fusion contracts for Layer 5."""

from __future__ import annotations

from dataclasses import dataclass

from software.layer4_inference import AnomalyDecision


@dataclass(frozen=True, slots=True)
class TriggerSignals:
    """External binary trigger inputs from auxiliary sensors."""

    pir_motion: bool = False
    thermal_presence: bool = False


@dataclass(frozen=True, slots=True)
class FusionResult:
    """Combined score and evidence produced by Layer 5."""

    frame_number: int
    timestamp_ms: float
    fused_score: float
    evidence: dict[str, float]


class SensorFusion:
    """Weighted score fusion between ML decision and trigger sensors."""

    def __init__(self, model_weight: float = 0.8, trigger_weight: float = 0.2) -> None:
        self.model_weight = model_weight
        self.trigger_weight = trigger_weight

    def fuse(self, decision: AnomalyDecision, triggers: TriggerSignals) -> FusionResult:
        trigger_score = 0.5 * float(triggers.pir_motion) + 0.5 * float(triggers.thermal_presence)
        fused_score = (self.model_weight * decision.anomaly_score) + (self.trigger_weight * trigger_score)
        evidence = {
            "model_score": float(decision.anomaly_score),
            "trigger_score": float(trigger_score),
        }
        return FusionResult(
            frame_number=decision.frame_number,
            timestamp_ms=decision.timestamp_ms,
            fused_score=float(fused_score),
            evidence=evidence,
        )
