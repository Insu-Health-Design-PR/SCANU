"""Signal processing contract for Layer 2 — weapon-optimised edition.

When the radar is configured with the weapon-optimised profile (WPN_CONFIG) the
IWR6843 outputs a real Range-Doppler heatmap (TLV 5) and Range-Azimuth heatmap
(TLV 4).  This processor uses those directly instead of the legacy 1D-range-profile
→ reshape → fake-FFT chain.
"""

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
    micro_doppler_bandwidth: float = 0.0
    doppler_centroid: float = 0.0
    doppler_spread: float = 0.0
    azimuth_static_peak: float = 0.0
    num_range_bins: int = 0
    num_doppler_bins: int = 0


class SignalProcessor:
    """Converts Layer 1 inputs into FFT + CFAR outputs.

    Priority order for signal extraction:
    1. TLV 5 range-doppler heatmap  (real 2D, weapon-optimised config)
    2. TLV 4 azimuth-static heatmap  (for stationary weapon detection)
    3. Legacy range_profile → reshape → fake-FFT  (backward compat)
    """

    def __init__(
        self,
        background: BackgroundModel | None = None,
        doppler_bins: int = 16,
        cfar_guard: int = 1,
        cfar_train: int = 2,
        cfar_threshold_scale: float = 1.8,
        weapon_cfar_threshold_scale: float = 1.2,
        num_range_bins: int = 256,
        time_fn: Callable[[], float] | None = None,
    ) -> None:
        if doppler_bins <= 0:
            raise ValueError("doppler_bins must be > 0")
        self._background = background if background is not None else BackgroundModel()
        self._doppler_bins = doppler_bins
        self._cfar_guard = max(0, cfar_guard)
        self._cfar_train = max(1, cfar_train)
        self._cfar_threshold_scale = max(0.1, cfar_threshold_scale)
        self._weapon_cfar_threshold_scale = max(0.1, weapon_cfar_threshold_scale)
        self._num_range_bins = num_range_bins
        self._time_fn = time_fn if time_fn is not None else time.time

    def process(self, frame: bytes | bytearray | memoryview | Any) -> ProcessedFrame:
        normalized = self._normalize_input(frame)

        rd_map, num_range, num_doppler = self._extract_range_doppler(normalized)
        detection_mask = self._cfar_2d(rd_map)

        point_cloud = normalized.point_cloud
        if point_cloud.size == 0:
            point_cloud = self._mask_to_point_cloud(rd_map, detection_mask)
        else:
            extra_mask = self._cfar_2d(rd_map, threshold_scale=self._weapon_cfar_threshold_scale)
            extra_cloud = self._mask_to_point_cloud(rd_map, extra_mask)
            if extra_cloud.size > 0:
                extra_padded = np.zeros((extra_cloud.shape[0], point_cloud.shape[1]), dtype=np.float32)
                extra_padded[:, : extra_cloud.shape[1]] = extra_cloud
                point_cloud = np.vstack([point_cloud, extra_padded])

        micro_dop_bw, dop_centroid, dop_spread = self._compute_micro_doppler(rd_map)
        azimuth_static_peak = self._compute_azimuth_static_peak(normalized)

        return ProcessedFrame(
            frame_number=normalized.frame_number,
            timestamp_ms=normalized.timestamp_ms,
            range_doppler=rd_map.astype(np.float32),
            point_cloud=point_cloud,
            source_timestamp_cycles=normalized.source_timestamp_cycles,
            micro_doppler_bandwidth=micro_dop_bw,
            doppler_centroid=dop_centroid,
            doppler_spread=dop_spread,
            azimuth_static_peak=azimuth_static_peak,
            num_range_bins=num_range,
            num_doppler_bins=num_doppler,
        )

    @dataclass(frozen=True, slots=True)
    class _NormalizedInput:
        frame_number: int
        timestamp_ms: float
        signal: np.ndarray
        point_cloud: np.ndarray
        range_doppler_raw: np.ndarray | None = None
        azimuth_static_raw: np.ndarray | None = None
        num_doppler_bins: int = 0
        num_range_bins: int = 256
        source_timestamp_cycles: int | None = None

    @staticmethod
    def _get_field(obj: Any, name: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    @classmethod
    def _has_field(cls, obj: Any, name: str) -> bool:
        return cls._get_field(obj, name, None) is not None

    def _normalize_input(self, frame: bytes | bytearray | memoryview | Any) -> _NormalizedInput:
        if isinstance(frame, (bytes, bytearray, memoryview)):
            return self._normalize_parsed_frame(self._parse_layer1_raw_frame(bytes(frame)))

        return self._normalize_parsed_frame(frame)

    def _normalize_parsed_frame(
        self,
        frame: Any,
        timestamp_ms_override: float | None = None,
    ) -> _NormalizedInput:
        range_doppler_raw = self._get_field(frame, "range_doppler_heatmap")
        azimuth_static_raw = self._get_field(frame, "azimuth_static_heatmap")

        signal = self._extract_signal(frame)
        point_cloud = self._extract_point_cloud(frame)
        frame_number = int(self._get_field(frame, "frame_number", 0))
        source_timestamp_cycles = self._extract_timestamp_cycles(frame)
        timestamp_ms = self._resolve_timestamp_ms(frame)

        if timestamp_ms_override is not None:
            timestamp_ms = timestamp_ms_override
        elif timestamp_ms is None:
            timestamp_ms = self._time_fn() * 1000.0

        num_doppler = 0
        if range_doppler_raw is not None:
            num_doppler = range_doppler_raw.size // self._num_range_bins if range_doppler_raw.size > 0 else 0

        return self._NormalizedInput(
            frame_number=frame_number,
            timestamp_ms=timestamp_ms,
            signal=signal,
            point_cloud=point_cloud,
            range_doppler_raw=range_doppler_raw,
            azimuth_static_raw=azimuth_static_raw,
            num_doppler_bins=num_doppler,
            num_range_bins=self._num_range_bins,
            source_timestamp_cycles=source_timestamp_cycles,
        )

    def _resolve_timestamp_ms(self, frame: Any) -> float | None:
        timestamp_ms = self._get_field(frame, "timestamp_ms")
        if timestamp_ms is not None:
            return float(timestamp_ms)
        return None

    def _extract_timestamp_cycles(self, frame: Any) -> int | None:
        timestamp_cycles = self._get_field(frame, "timestamp_cycles")
        if timestamp_cycles is not None:
            return int(timestamp_cycles)
        timestamp_cycles = self._get_field(frame, "timestamp")
        if timestamp_cycles is not None:
            return int(timestamp_cycles)
        return None

    # ── signal extraction ──────────────────────────────────────────────

    def _extract_signal(self, frame: Any) -> np.ndarray:
        range_doppler = self._get_field(frame, "range_doppler_heatmap")
        azimuth_static = self._get_field(frame, "azimuth_static_heatmap")
        range_profile = self._get_field(frame, "range_profile")
        noise_profile = self._get_field(frame, "noise_profile")
        points = self._get_field(frame, "points")

        if range_doppler is not None:
            return np.asarray(range_doppler, dtype=np.float32).reshape(-1)
        if azimuth_static is not None:
            return np.asarray(azimuth_static, dtype=np.float32).reshape(-1)
        if range_profile is not None:
            return np.asarray(range_profile, dtype=np.float32).reshape(-1)
        if noise_profile is not None:
            return np.asarray(noise_profile, dtype=np.float32).reshape(-1)
        if points is not None:
            return self._points_to_signal(points)

        raise TypeError("SignalProcessor.process expects Layer 1 raw bytes or a parsed Layer 1 frame")

    def _extract_point_cloud(self, frame: Any) -> np.ndarray:
        get_point_cloud_with_snr = self._get_field(frame, "get_point_cloud_with_snr")
        if callable(get_point_cloud_with_snr):
            point_cloud = np.asarray(get_point_cloud_with_snr(), dtype=np.float32)
            if point_cloud.size > 0:
                return point_cloud

        get_point_cloud = self._get_field(frame, "get_point_cloud")
        if callable(get_point_cloud):
            point_cloud = np.asarray(get_point_cloud(), dtype=np.float32)
            if point_cloud.size > 0:
                return point_cloud

        points = self._get_field(frame, "points")
        if points is None:
            return np.empty((0, 3), dtype=np.float32)

        if not points:
            return np.empty((0, 3), dtype=np.float32)

        rows: list[list[float]] = []
        for point in points:
            values = [
                float(self._get_field(point, "x", 0.0)),
                float(self._get_field(point, "y", 0.0)),
                float(self._get_field(point, "z", 0.0)),
            ]
            if self._has_field(point, "doppler"):
                values.append(float(self._get_field(point, "doppler", 0.0)))
            if self._has_field(point, "snr"):
                values.append(float(self._get_field(point, "snr", 0.0)))
            if self._has_field(point, "noise"):
                values.append(float(self._get_field(point, "noise", 0.0)))
            rows.append(values)

        return np.asarray(rows, dtype=np.float32)

    def _parse_layer1_raw_frame(self, frame: bytes) -> Any:
        from software.layer1_radar.mmwave.tlv_parser import parse_frame

        return parse_frame(frame)

    def _points_to_signal(self, points: Any) -> np.ndarray:
        if not points:
            return np.zeros(0, dtype=np.float32)
        samples: list[float] = []
        for point in points:
            samples.extend(
                [
                    float(self._get_field(point, "x", 0.0)),
                    float(self._get_field(point, "y", 0.0)),
                    float(self._get_field(point, "z", 0.0)),
                    float(self._get_field(point, "doppler", 0.0)),
                ]
            )
        return np.asarray(samples, dtype=np.float32)

    # ── Range-Doppler extraction ────────────────────────────────────────

    def _extract_range_doppler(
        self, normalized: _NormalizedInput
    ) -> tuple[np.ndarray, int, int]:
        if normalized.range_doppler_raw is not None and normalized.num_doppler_bins > 1:
            rd = normalized.range_doppler_raw.reshape(
                (normalized.num_doppler_bins, -1)
            ).T
            rd = np.abs(rd)
            rd = np.fft.fftshift(rd, axes=1)
            n_range, n_dopp = rd.shape
            return rd.astype(np.float32), n_range, n_dopp

        signal = normalized.signal
        calibrated = self._calibrate(signal)
        matrix = self._reshape_for_fft(calibrated)
        spectrum = self._range_doppler_fft(matrix)
        return spectrum.astype(np.float32), spectrum.shape[0], spectrum.shape[1]

    # ── Micro-Doppler analysis ──────────────────────────────────────────

    def _compute_micro_doppler(
        self, rd_map: np.ndarray
    ) -> tuple[float, float, float]:
        doppler_profile = np.sum(rd_map, axis=0, dtype=np.float32)
        total_power = float(np.sum(doppler_profile))
        if total_power <= 0:
            return 0.0, 0.0, 0.0

        n_bins = doppler_profile.size
        doppler_profile /= total_power

        centroid = float(np.sum(np.arange(n_bins) * doppler_profile))
        variance = float(np.sum(((np.arange(n_bins) - centroid) ** 2) * doppler_profile))
        spread = float(np.sqrt(max(variance, 0.0)))

        threshold = float(np.max(doppler_profile)) * 0.1
        significant = np.where(doppler_profile > threshold)[0]
        if significant.size >= 2:
            bandwidth_raw = float(significant[-1] - significant[0])
        else:
            bandwidth_raw = spread * 2.0

        bandwidth = bandwidth_raw / n_bins

        doppler_profile_norm = (doppler_profile - np.min(doppler_profile))
        range_denom = float(np.max(doppler_profile_norm))
        if range_denom > 0:
            doppler_profile_norm /= range_denom
        centroid_norm = centroid / n_bins
        spread_norm = spread / n_bins

        return bandwidth, centroid_norm, spread_norm

    # ── Azimuth-static analysis ─────────────────────────────────────────

    def _compute_azimuth_static_peak(self, normalized: _NormalizedInput) -> float:
        az_map = normalized.azimuth_static_raw
        if az_map is None or az_map.size == 0:
            return 0.0
        return float(np.max(np.abs(az_map)))

    # ── Calibration ─────────────────────────────────────────────────────

    def _calibrate(self, sample: np.ndarray) -> np.ndarray:
        self._background.update(sample)
        return self._background.subtract(sample)

    # ── Legacy helpers (used when TLV 5 is absent) ──────────────────────

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

    # ── CFAR ────────────────────────────────────────────────────────────

    def _cfar_2d(
        self, rd_map: np.ndarray, threshold_scale: float | None = None
    ) -> np.ndarray:
        scale = threshold_scale if threshold_scale is not None else self._cfar_threshold_scale
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
                threshold = noise * scale
                if rd_map[r, c] > threshold:
                    mask[r, c] = True

        return mask

    def _mask_to_point_cloud(self, rd_map: np.ndarray, mask: np.ndarray) -> np.ndarray:
        idx = np.argwhere(mask)
        if idx.size == 0:
            return np.empty((0, 3), dtype=np.float32)

        strengths = rd_map[idx[:, 0], idx[:, 1]]
        top_n = min(32, strengths.size)
        keep = np.argsort(strengths)[-top_n:]
        picks = idx[keep]
        vals = strengths[keep]
        return np.column_stack((picks.astype(np.float32), vals.astype(np.float32)))
