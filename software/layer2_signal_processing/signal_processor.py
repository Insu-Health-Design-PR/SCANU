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
    """Converts raw bytes into calibrated tensors expected by Layer 3."""

    def __init__(self, background: BackgroundModel | None = None, doppler_bins: int = 16) -> None:
        if doppler_bins <= 0:
            raise ValueError("doppler_bins must be > 0")
        self._background = background if background is not None else BackgroundModel()
        self._doppler_bins = doppler_bins

    def process(self, frame: RadarFrame) -> ProcessedFrame:
        magnitude = np.frombuffer(frame.payload, dtype=np.uint8).astype(np.float32)
        if magnitude.size == 0:
            magnitude = np.zeros(self._doppler_bins, dtype=np.float32)

        calibrated = self._calibrate(magnitude)
        range_doppler = self._to_range_doppler(calibrated)
        point_cloud = self._to_point_cloud(range_doppler)

        return ProcessedFrame(
            frame_number=frame.frame_number,
            timestamp_ms=frame.timestamp_ms,
            range_doppler=range_doppler,
            point_cloud=point_cloud,
        )

    def _calibrate(self, sample: np.ndarray) -> np.ndarray:
        self._background.update(sample)
        return self._background.subtract(sample)

    def _to_range_doppler(self, sample: np.ndarray) -> np.ndarray:
        bins = self._doppler_bins
        rows = int(np.ceil(sample.size / bins))
        padded = np.zeros(rows * bins, dtype=np.float32)
        padded[: sample.size] = sample
        return padded.reshape(rows, bins)

    def _to_point_cloud(self, range_doppler: np.ndarray) -> np.ndarray:
        # Lightweight deterministic extraction: pick the top-3 positive cells.
        flat = range_doppler.ravel()
        positive_idx = np.where(flat > 0.0)[0]
        if positive_idx.size == 0:
            return np.empty((0, 3), dtype=np.float32)

        top_k = positive_idx[np.argsort(flat[positive_idx])[-3:]]
        rows, cols = np.unravel_index(top_k, range_doppler.shape)
        intensities = flat[top_k]
        return np.stack((rows.astype(np.float32), cols.astype(np.float32), intensities), axis=1)
