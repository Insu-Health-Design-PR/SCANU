"""Signal processing contract for Layer 2."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable

import numpy as np

from .calibration import BackgroundModel


@dataclass(frozen=True, slots=True)
class ProcessedFrame:
    """Normalized outputs consumed by downstream feature extraction."""

    frame_number: int
    timestamp_ms: float
    range_doppler: np.ndarray
    point_cloud: np.ndarray
    source_timestamp_cycles: int | None = None


class SignalProcessor:
    """Converts Layer 1 inputs into FFT + CFAR outputs.

    Supports:
    - Raw UART frame bytes emitted by Layer 1.
    - Parsed Layer 1 frame-like objects exposing ``range_profile`` and/or
      ``points`` attributes from the TLV parser.
    """

    def __init__(
        self,
        background: BackgroundModel | None = None,
        doppler_bins: int = 16,
        cfar_guard: int = 1,
        cfar_train: int = 2,
        cfar_threshold_scale: float = 1.8,
        time_fn: Callable[[], float] | None = None,
    ) -> None:
        if doppler_bins <= 0:
            raise ValueError("doppler_bins must be > 0")
        self._background = background if background is not None else BackgroundModel()
        self._doppler_bins = doppler_bins
        self._cfar_guard = max(0, cfar_guard)
        self._cfar_train = max(1, cfar_train)
        self._cfar_threshold_scale = max(0.1, cfar_threshold_scale)
        self._time_fn = time_fn if time_fn is not None else time.time

    def process(self, frame: bytes | bytearray | memoryview | Any) -> ProcessedFrame:
        normalized = self._normalize_input(frame)

        calibrated = self._calibrate(normalized.signal)
        matrix = self._reshape_for_fft(calibrated)
        spectrum = self._range_doppler_fft(matrix)
        detection_mask = self._cfar_2d(spectrum)

        range_doppler = spectrum.astype(np.float32)
        point_cloud = normalized.point_cloud
        if point_cloud.size == 0:
            point_cloud = self._mask_to_point_cloud(range_doppler, detection_mask)

        return ProcessedFrame(
            frame_number=normalized.frame_number,
            timestamp_ms=normalized.timestamp_ms,
            range_doppler=range_doppler,
            point_cloud=point_cloud,
            source_timestamp_cycles=normalized.source_timestamp_cycles,
        )

    @dataclass(frozen=True, slots=True)
    class _NormalizedInput:
        frame_number: int
        timestamp_ms: float
        signal: np.ndarray
        point_cloud: np.ndarray
        source_timestamp_cycles: int | None = None

    def _normalize_input(self, frame: bytes | bytearray | memoryview | Any) -> _NormalizedInput:
        if isinstance(frame, (bytes, bytearray, memoryview)):
            return self._normalize_parsed_frame(self._parse_layer1_raw_frame(bytes(frame)))

        return self._normalize_parsed_frame(frame)

    def _normalize_parsed_frame(
        self,
        frame: Any,
        timestamp_ms_override: float | None = None,
    ) -> _NormalizedInput:
        signal = self._extract_signal(frame)
        point_cloud = self._extract_point_cloud(frame)
        frame_number = int(getattr(frame, "frame_number", 0))
        source_timestamp_cycles = self._extract_timestamp_cycles(frame)
        timestamp_ms = self._resolve_timestamp_ms(frame)

        if timestamp_ms_override is not None:
            timestamp_ms = timestamp_ms_override
        elif timestamp_ms is None:
            timestamp_ms = self._time_fn() * 1000.0

        return self._NormalizedInput(
            frame_number=frame_number,
            timestamp_ms=timestamp_ms,
            signal=signal,
            point_cloud=point_cloud,
            source_timestamp_cycles=source_timestamp_cycles,
        )

    def _resolve_timestamp_ms(self, frame: Any) -> float | None:
        if hasattr(frame, "timestamp_ms"):
            return float(frame.timestamp_ms)
        return None

    def _extract_timestamp_cycles(self, frame: Any) -> int | None:
        if hasattr(frame, "timestamp_cycles"):
            return int(frame.timestamp_cycles)
        return None

    def _extract_signal(self, frame: Any) -> np.ndarray:
        if hasattr(frame, "range_profile") and frame.range_profile is not None:
            signal = np.asarray(frame.range_profile, dtype=np.float32).reshape(-1)
        elif hasattr(frame, "noise_profile") and frame.noise_profile is not None:
            signal = np.asarray(frame.noise_profile, dtype=np.float32).reshape(-1)
        elif hasattr(frame, "points"):
            signal = self._points_to_signal(getattr(frame, "points"))
        else:
            raise TypeError("SignalProcessor.process expects Layer 1 raw bytes or a parsed Layer 1 frame")

        if signal.size == 0:
            return np.zeros(self._doppler_bins * 2, dtype=np.float32)
        return signal

    def _extract_point_cloud(self, frame: Any) -> np.ndarray:
        if hasattr(frame, "get_point_cloud_with_snr"):
            point_cloud = np.asarray(frame.get_point_cloud_with_snr(), dtype=np.float32)
            if point_cloud.size > 0:
                return point_cloud

        if hasattr(frame, "get_point_cloud"):
            point_cloud = np.asarray(frame.get_point_cloud(), dtype=np.float32)
            if point_cloud.size > 0:
                return point_cloud

        if not hasattr(frame, "points"):
            return np.empty((0, 3), dtype=np.float32)

        points = getattr(frame, "points")
        if not points:
            return np.empty((0, 3), dtype=np.float32)

        rows: list[list[float]] = []
        for point in points:
            values = [
                float(getattr(point, "x", 0.0)),
                float(getattr(point, "y", 0.0)),
                float(getattr(point, "z", 0.0)),
            ]

            if hasattr(point, "doppler"):
                values.append(float(point.doppler))
            if hasattr(point, "snr"):
                values.append(float(point.snr))
            if hasattr(point, "noise"):
                values.append(float(point.noise))

            rows.append(values)

        return np.asarray(rows, dtype=np.float32)

    def _parse_layer1_raw_frame(self, frame: bytes) -> Any:
        from software.layer1_radar.tlv_parser import parse_frame

        return parse_frame(frame)

    def _points_to_signal(self, points: Any) -> np.ndarray:
        if not points:
            return np.zeros(0, dtype=np.float32)

        samples: list[float] = []
        for point in points:
            samples.extend(
                [
                    float(getattr(point, "x", 0.0)),
                    float(getattr(point, "y", 0.0)),
                    float(getattr(point, "z", 0.0)),
                    float(getattr(point, "doppler", 0.0)),
                ]
            )

        return np.asarray(samples, dtype=np.float32)

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
