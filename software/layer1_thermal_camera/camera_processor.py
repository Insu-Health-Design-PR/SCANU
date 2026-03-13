"""Thermal frame feature extraction for presence and hotspot scoring."""

from __future__ import annotations

import numpy as np

from .camera_models import ThermalFeatures, ThermalFrame


class ThermalProcessor:
    """Extracts lightweight presence-oriented features from thermal frames."""

    def __init__(self, hotspot_threshold_c: float = 28.0) -> None:
        self._hotspot_threshold_c = hotspot_threshold_c

    def extract(self, frame: ThermalFrame) -> ThermalFeatures:
        data = np.asarray(frame.temperature_c, dtype=np.float32)
        max_temp = float(np.max(data)) if data.size else 0.0
        mean_temp = float(np.mean(data)) if data.size else 0.0

        if data.size == 0:
            hotspot_ratio = 0.0
        else:
            hotspot_ratio = float(np.mean(data >= self._hotspot_threshold_c))

        # Lightweight deterministic mapping to [0, 1].
        presence_score = float(np.clip(hotspot_ratio * 2.0, 0.0, 1.0))

        return ThermalFeatures(
            frame_number=frame.frame_number,
            timestamp_ms=frame.timestamp_ms,
            max_temp_c=max_temp,
            mean_temp_c=mean_temp,
            hotspot_ratio=hotspot_ratio,
            presence_score=presence_score,
        )
