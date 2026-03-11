"""Inference engine contracts for Layer 4."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from software.layer3_features import FeatureBatch


@dataclass(frozen=True, slots=True)
class InferenceResult:
    """Raw model-like score and confidence for a frame."""

    frame_number: int
    timestamp_ms: float
    raw_score: float
    confidence: float


class InferenceEngine:
    """Lightweight deterministic inference approximation."""

    def infer(self, features: FeatureBatch) -> InferenceResult:
        vector = np.asarray(features.vector, dtype=np.float32)
        mean_val = float(np.mean(vector)) if vector.size else 0.0
        raw_score = float(np.clip((mean_val + 1.0) / 2.0, 0.0, 1.0))
        confidence = float(np.clip(abs(mean_val), 0.0, 1.0))
        return InferenceResult(
            frame_number=features.frame_number,
            timestamp_ms=features.timestamp_ms,
            raw_score=raw_score,
            confidence=confidence,
        )
