"""Deterministic multi-sensor fusion using logic rules on all three sensors.

Consumes `MultiModalFeatures` from Layer 3 and applies deterministic
logic rules to produce a `FusionInputContract` for Layer 6.

Scoring strategy (three pillars):
  1. mmWave coherence + CFAR zone count → metal object evidence
  2. Thermal cold-spot detection → metal thermal signature
  3. RGB visual cues (skin concealment, waist anomaly) → suspicious
"""

from __future__ import annotations

import time
from typing import Any, Optional

import numpy as np

from layer3_features.multimodal_features import (
    MultiModalFeatureExtractor,
    MultiModalFeatures,
)
from layer5_fusion.models import FusionInputContract


class DeterministicFusionAdapter:
    """Logic-based multi-sensor fusion using mmWave + RGB + Thermal."""

    def __init__(self, extractor: Optional[MultiModalFeatureExtractor] = None):
        self._extractor = extractor or MultiModalFeatureExtractor()

    def adapt(
        self,
        raw_inputs: Any,
        *,
        radar_id: str = "radar_main",
        now_ms: float | None = None,
    ) -> FusionInputContract:
        """Produce a scored FusionInputContract from raw multi-sensor inputs."""
        if isinstance(raw_inputs, FusionInputContract):
            return raw_inputs

        ts = float(now_ms if now_ms is not None else time.time() * 1000.0)
        frame_number = int(self._get(raw_inputs, "frame_number", 0))

        mmwave_result = self._get(raw_inputs, "mmwave_result")
        rgb_frame = self._get(raw_inputs, "rgb_frame")
        thermal_frame = self._get(raw_inputs, "thermal_frame")

        features = self._extractor.extract(mmwave_result, rgb_frame, thermal_frame)
        fused_score = features.deterministic_score()

        evidence = features.to_evidence_dict()

        anomaly_score = float(np.clip(fused_score * 1.15, 0.0, 1.0))

        trigger_score = float(max(
            evidence.get("zone_coherence_max", 0.0),
            evidence.get("n_cfar_detections_zone", 0.0) / 50.0,
            evidence.get("thermal_cold_spot_pct", 0.0) / 5.0,
            fused_score,
        ))

        sensors_on = sum([
            1 if mmwave_result is not None else 0,
            1 if rgb_frame is not None else 0,
            1 if thermal_frame is not None else 0,
        ])
        confidence = float(np.clip(
            0.30 + 0.10 * sensors_on + 0.40 * fused_score + 0.15 * evidence.get("mean_snr", 0.0),
            0.0, 1.0,
        ))

        return FusionInputContract(
            frame_number=frame_number,
            timestamp_ms=float(self._get(raw_inputs, "timestamp_ms", ts)),
            radar_id=str(self._get(raw_inputs, "radar_id", radar_id) or radar_id),
            fused_score=fused_score,
            confidence=confidence,
            trigger_score=trigger_score,
            anomaly_score=anomaly_score,
            source_mode="deterministic_3_sensor",
            evidence=evidence,
        )

    @staticmethod
    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
