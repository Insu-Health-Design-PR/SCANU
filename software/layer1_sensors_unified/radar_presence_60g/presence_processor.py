"""Lightweight processing for 60 GHz presence radar features."""

from __future__ import annotations

import numpy as np

from .presence_models import PresenceFeatures, PresenceFrame


class PresenceProcessor:
    """Normalizes raw presence readings into fusion-ready features."""

    def __init__(self, presence_threshold: float = 0.5) -> None:
        self._presence_threshold = presence_threshold

    def extract(self, frame: PresenceFrame) -> PresenceFeatures:
        presence_score = float(np.clip(frame.presence_raw, 0.0, 1.0))
        motion_score = float(np.clip(frame.motion_raw, 0.0, 1.0))
        signal_quality = float(np.clip(frame.signal_quality, 0.0, 1.0))
        confidence = float(
            np.clip(((presence_score + motion_score) * 0.5) * signal_quality, 0.0, 1.0)
        )
        is_present = presence_score >= self._presence_threshold

        return PresenceFeatures(
            frame_number=frame.frame_number,
            timestamp_ms=frame.timestamp_ms,
            presence_score=presence_score,
            motion_score=motion_score,
            confidence=confidence,
            is_present=is_present,
            distance_m=frame.distance_m,
            signal_quality=signal_quality,
            sensor_model=frame.sensor_model,
            board_kit=frame.board_kit,
        )
