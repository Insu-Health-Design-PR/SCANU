"""Temporary L1/L2 -> Layer 6 fusion input adapter."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from .models import FusionInputContract


class L1L2FusionAdapter:
    """Builds a provisional fusion score from available Layer 1/2 signals."""

    def __init__(self, *, mmwave_max_points: int = 12, thermal_alpha: float = 0.05) -> None:
        self._mmwave_max_points = max(1, int(mmwave_max_points))
        self._thermal_alpha = float(np.clip(thermal_alpha, 0.001, 1.0))
        self._thermal_baseline_mean: float | None = None

    @staticmethod
    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _thermal_score(self, thermal_frame_bgr: Any, direct_value: Any = None) -> float:
        if direct_value is not None:
            try:
                return float(np.clip(float(direct_value), 0.0, 1.0))
            except Exception:
                return 0.0

        if thermal_frame_bgr is None:
            return 0.0

        arr = np.asarray(thermal_frame_bgr)
        if arr.size == 0:
            return 0.0

        # Mean intensity delta vs slowly adapting baseline.
        mean_val = float(np.mean(arr.astype(np.float32)))
        if self._thermal_baseline_mean is None:
            self._thermal_baseline_mean = mean_val

        baseline = float(self._thermal_baseline_mean)
        delta = abs(mean_val - baseline)
        self._thermal_baseline_mean = (1.0 - self._thermal_alpha) * baseline + self._thermal_alpha * mean_val

        # Normalize from image-space delta to [0, 1] trigger-like score.
        return float(np.clip(delta / 35.0, 0.0, 1.0))

    def adapt(self, raw_inputs: Any, *, radar_id: str = "radar_main", now_ms: float | None = None) -> FusionInputContract:
        """Convert raw Layer 1/2 frame bundle into `FusionInputContract`."""

        if isinstance(raw_inputs, FusionInputContract):
            return raw_inputs

        ts = float(now_ms if now_ms is not None else time.time() * 1000.0)
        frame_number = int(self._get(raw_inputs, "frame_number", 0))
        frame_ts = self._get(raw_inputs, "timestamp_ms", ts)

        mmwave_frame = self._get(raw_inputs, "mmwave_frame")
        presence_frame = self._get(raw_inputs, "presence_frame")
        thermal_frame = self._get(raw_inputs, "thermal_frame_bgr")

        if mmwave_frame is None:
            mmwave_frame = self._get(raw_inputs, "layer2_processed")

        points = self._get(mmwave_frame, "points", []) if mmwave_frame is not None else []
        point_count = len(points) if points is not None else 0
        mmwave_score = float(np.clip(point_count / float(self._mmwave_max_points), 0.0, 1.0))

        presence_raw = float(self._get(presence_frame, "presence_raw", 0.0) or 0.0)
        motion_raw = float(self._get(presence_frame, "motion_raw", 0.0) or 0.0)
        presence_score = float(np.clip(presence_raw, 0.0, 1.0))
        motion_score = float(np.clip(motion_raw, 0.0, 1.0))

        thermal_direct = self._get(raw_inputs, "thermal_presence", None)
        thermal_score = self._thermal_score(thermal_frame, direct_value=thermal_direct)

        trigger_score = float(max(mmwave_score, presence_score, motion_score, thermal_score))

        anomaly_score = float(
            np.clip(
                0.50 * mmwave_score
                + 0.20 * presence_score
                + 0.20 * motion_score
                + 0.10 * thermal_score,
                0.0,
                1.0,
            )
        )

        fused_override = self._get(raw_inputs, "fused_score", None)
        if fused_override is not None:
            try:
                fused_score = float(np.clip(float(fused_override), 0.0, 1.0))
            except Exception:
                fused_score = anomaly_score
        else:
            fused_score = anomaly_score

        signals_available = 1  # mmWave always considered, even if empty.
        signals_available += 1 if presence_frame is not None else 0
        signals_available += 1 if thermal_frame is not None or thermal_direct is not None else 0
        confidence = float(np.clip(0.35 + 0.2 * signals_available + 0.45 * max(0.0, mmwave_score), 0.0, 1.0))

        return FusionInputContract(
            frame_number=frame_number,
            timestamp_ms=float(frame_ts),
            radar_id=str(self._get(raw_inputs, "radar_id", radar_id) or radar_id),
            fused_score=fused_score,
            confidence=confidence,
            trigger_score=trigger_score,
            anomaly_score=anomaly_score,
            source_mode="provisional_l1_l2",
            evidence={
                "mmwave_score": mmwave_score,
                "presence_score": presence_score,
                "motion_score": motion_score,
                "thermal_score": thermal_score,
                "signals_available": float(signals_available),
                "point_count": float(point_count),
            },
        )
