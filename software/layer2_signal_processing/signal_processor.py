"""Signal processing contract for Layer 2."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .calibration import BackgroundModel
from .frame_buffer import RadarFrame


@dataclass(frozen=True, slots=True)
class ProcessedFrame:
    """Normalized outputs consumed by downstream feature extraction."""

    frame_number: int
    timestamp_ms: float
    range_doppler: np.ndarray
    point_cloud: np.ndarray


class SignalProcessor:
    """Converts raw bytes into FFT + CFAR outputs."""

    def __init__(
        self,
        background: BackgroundModel | None = None,
        doppler_bins: int = 16,
        cfar_guard: int = 1,
        cfar_train: int = 2,
        cfar_threshold_scale: float = 1.8,
    ) -> None:
        if doppler_bins <= 0:
            raise ValueError("doppler_bins must be > 0")
        self._background = background if background is not None else BackgroundModel()
        self._doppler_bins = doppler_bins
        self._cfar_guard = max(0, cfar_guard)
        self._cfar_train = max(1, cfar_train)
        self._cfar_threshold_scale = max(0.1, cfar_threshold_scale)

    def process(self, frame: RadarFrame) -> ProcessedFrame:
        signal = np.frombuffer(frame.payload, dtype=np.uint8).astype(np.float32)
        if signal.size == 0:
            signal = np.zeros(self._doppler_bins * 2, dtype=np.float32)

        calibrated = self._calibrate(signal)
        matrix = self._reshape_for_fft(calibrated)
        spectrum = self._range_doppler_fft(matrix)
        detection_mask = self._cfar_2d(spectrum)

        range_doppler = spectrum.astype(np.float32)
        point_cloud = self._mask_to_point_cloud(range_doppler, detection_mask)

        return ProcessedFrame(
            frame_number=frame.frame_number,
            timestamp_ms=frame.timestamp_ms,
            range_doppler=range_doppler,
            point_cloud=point_cloud,
        )

    def _calibrate(self, sample: np.ndarray) -> np.ndarray:
        self._background.update(sample)
        return self._background.subtract(sample)

    def _reshape_for_fft(self, sample: np.ndarray) -> np.ndarray:
        rows = int(np.ceil(sample.size / self._doppler_bins))
        padded = np.zeros(rows * self._doppler_bins, dtype=np.float32)
        padded[: sample.size] = sample
        return padded.reshape(rows, self._doppler_bins)

    def _range_doppler_fft(self, matrix: np.ndarray) -> np.ndarray:
        range_fft = np.fft.fft(matrix, axis=1)
        doppler_fft = np.fft.fft(range_fft, axis=0)
        power = np.abs(doppler_fft)
        return np.fft.fftshift(power, axes=0)

    def _cfar_2d(self, rd_map: np.ndarray) -> np.ndarray:
        rows, cols = rd_map.shape
        mask = np.zeros((rows, cols), dtype=bool)
        win = self._cfar_guard + self._cfar_train

        for r in range(rows):
            r0 = max(0, r - win)
            r1 = min(rows, r + win + 1)
            for c in range(cols):
                c0 = max(0, c - win)
                c1 = min(cols, c + win + 1)

                window = rd_map[r0:r1, c0:c1]
                if window.size <= 1:
                    continue

                rr0 = max(0, (r - self._cfar_guard) - r0)
                rr1 = min(window.shape[0], (r + self._cfar_guard + 1) - r0)
                cc0 = max(0, (c - self._cfar_guard) - c0)
                cc1 = min(window.shape[1], (c + self._cfar_guard + 1) - c0)

                train_window = window.copy()
                train_window[rr0:rr1, cc0:cc1] = 0.0
                training_cells = train_window[train_window > 0.0]

                if training_cells.size == 0:
                    continue

                noise = float(np.mean(training_cells))
                threshold = noise * self._cfar_threshold_scale
                if rd_map[r, c] > threshold:
                    mask[r, c] = True

        return mask

    def _mask_to_point_cloud(self, rd_map: np.ndarray, mask: np.ndarray) -> np.ndarray:
        idx = np.argwhere(mask)
        if idx.size == 0:
            return np.empty((0, 3), dtype=np.float32)

        strengths = rd_map[idx[:, 0], idx[:, 1]]
        top_n = min(16, strengths.size)
        keep = np.argsort(strengths)[-top_n:]
        picks = idx[keep]
        vals = strengths[keep]
        return np.column_stack((picks.astype(np.float32), vals.astype(np.float32)))
