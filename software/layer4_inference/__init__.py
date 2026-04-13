"""Layer 4: thermal / vision threat inference."""

from layer4_inference.threat_engine import (
    AnomalyDecision,
    AnomalyScorer,
    InferenceEngine,
    InferenceResult,
    ThermalThreatDetector,
    ThreatDetection,
)

__all__ = [
    "AnomalyDecision",
    "AnomalyScorer",
    "InferenceEngine",
    "InferenceResult",
    "ThermalThreatDetector",
    "ThreatDetection",
]
