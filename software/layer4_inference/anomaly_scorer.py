"""Anomaly scoring contract for Layer 4."""

from __future__ import annotations

from dataclasses import dataclass

from .inference_engine import InferenceResult


@dataclass(frozen=True, slots=True)
class AnomalyDecision:
    """Thresholded anomaly decision exposed to Layer 5."""

    frame_number: int
    timestamp_ms: float
    anomaly_score: float
    confidence: float
    is_anomaly: bool


class AnomalyScorer:
    """Maps inference outputs into binary anomaly decisions."""

    def __init__(self, threshold: float = 0.35) -> None:
        self.threshold = threshold

    def evaluate(self, result: InferenceResult) -> AnomalyDecision:
        anomaly_score = float(result.raw_score * result.confidence)
        return AnomalyDecision(
            frame_number=result.frame_number,
            timestamp_ms=result.timestamp_ms,
            anomaly_score=anomaly_score,
            confidence=result.confidence,
            is_anomaly=anomaly_score >= self.threshold,
        )
