"""Signal processing contract for Layer 2."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .calibration import BackgroundModel
from .frame_buffer import RadarFrame


@dataclass(frozen=True, slots=True)
class ProcessedFrame:
    """Normalized outputs consumed by Layer 3."""

    frame_number: int
    timestamp_ms: float
    range_doppler: np.ndarray
    point_cloud: np.ndarray


class SignalProcessor:
    """Converts raw bytes into calibrated numeric tensors."""

    def __init__(self, background: BackgroundModel | None = None) -> None:
        self._background = background if background is not None else BackgroundModel()

    def process(self, frame: RadarFrame) -> ProcessedFrame:
        raw = np.frombuffer(frame.payload, dtype=np.uint8)
        magnitude = raw.astype(np.float32)
        self._background.update(magnitude)
        range_doppler = self._background.subtract(magnitude)
        point_cloud = np.empty((0, 3), dtype=np.float32)
        return ProcessedFrame(
            frame_number=frame.frame_number,
            timestamp_ms=frame.timestamp_ms,
            range_doppler=range_doppler,
            point_cloud=point_cloud,
        )
