"""Inference engine for thermal/object-aware anomaly scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .thermal_detector import Detection, ThermalThreatDetector


@dataclass(frozen=True, slots=True)
class InferenceResult:
    frame_number: int
    timestamp_ms: float
    raw_score: float
    confidence: float
    threat_score: float
    person_count: int
    detections: list[Detection]


class InferenceEngine:
    """Computes a continuous threat/anomaly score from thermal detections."""

    THREAT_LABELS = {
        "gun",
        "pistol",
        "rifle",
        "weapon",
        "knife",
    }
    PERSON_LABELS = {
        "person",
        "people",
        "human",
    }

    def __init__(self, detector: ThermalThreatDetector | None = None) -> None:
        self.detector = detector or ThermalThreatDetector()

    @staticmethod
    def _score_labels(detections: Iterable[Detection]) -> tuple[float, int, float]:
        threat_score = 0.0
        person_count = 0
        max_conf = 0.0

        for d in detections:
            max_conf = max(max_conf, float(d.score))
            label = d.label.lower()
            if label in InferenceEngine.PERSON_LABELS:
                person_count += 1
            if any(k in label for k in InferenceEngine.THREAT_LABELS):
                threat_score = max(threat_score, float(d.score))

        return threat_score, person_count, max_conf

    def infer(self, frame_number: int, timestamp_ms: float, thermal_frame_bgr) -> InferenceResult:
        detections = self.detector.detect(thermal_frame_bgr)
        threat_score, person_count, max_conf = self._score_labels(detections)

        # Base scoring:
        # - threat detections dominate
        # - no explicit threat labels still keeps a weak anomaly prior if there are
        #   many confident detections in thermal scene.
        scene_density = min(1.0, len(detections) / 10.0)
        raw = float(np.clip(0.85 * threat_score + 0.15 * scene_density * max_conf, 0.0, 1.0))
        conf = float(np.clip(max_conf, 0.0, 1.0))

        return InferenceResult(
            frame_number=int(frame_number),
            timestamp_ms=float(timestamp_ms),
            raw_score=raw,
            confidence=conf,
            threat_score=float(threat_score),
            person_count=int(person_count),
            detections=detections,
        )

