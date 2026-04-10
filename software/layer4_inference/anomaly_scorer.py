"""Thresholding layer for inference results."""

from __future__ import annotations

from dataclasses import dataclass

from .inference_engine import InferenceResult


@dataclass(frozen=True, slots=True)
class AnomalyDecision:
    frame_number: int
    timestamp_ms: float
    anomaly_score: float
    confidence: float
    is_anomaly: bool
    label: str


class AnomalyScorer:
    """
    Converts continuous scores into labels.

    Labels:
    - unarmed
    - suspicious
    - armed
    """

    def __init__(
        self,
        *,
        suspicious_threshold: float = 0.25,
        armed_threshold: float = 0.55,
        min_confidence: float = 0.20,
    ) -> None:
        self.suspicious_threshold = float(suspicious_threshold)
        self.armed_threshold = float(armed_threshold)
        self.min_confidence = float(min_confidence)

    def evaluate(self, result: InferenceResult) -> AnomalyDecision:
        score = float(result.raw_score)
        conf = float(result.confidence)

        if conf < self.min_confidence:
            label = "unarmed"
            is_anomaly = False
        elif score >= self.armed_threshold:
            label = "armed"
            is_anomaly = True
        elif score >= self.suspicious_threshold:
            label = "suspicious"
            is_anomaly = True
        else:
            label = "unarmed"
            is_anomaly = False

        return AnomalyDecision(
            frame_number=result.frame_number,
            timestamp_ms=result.timestamp_ms,
            anomaly_score=score,
            confidence=conf,
            is_anomaly=is_anomaly,
            label=label,
        )

