"""Utilities to filter noisy mmWave detections before visualization."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class RadarPointFilterConfig:
    """Geometry and quality gates for Layer 1 mmWave detections."""

    min_range_m: float = 0.35
    max_range_m: float = 6.0
    max_abs_azimuth_deg: float = 65.0
    min_z_m: float = -1.0
    max_z_m: float = 2.5
    min_snr_db: float = 6.0
    max_abs_doppler_mps: float = 6.0


def _get_attr(point: Any, name: str, default: float = 0.0) -> float:
    return float(getattr(point, name, default))


def filter_detected_points(points: Iterable[Any], cfg: RadarPointFilterConfig) -> list[Any]:
    """Return points that pass range/FOV/SNR gates."""

    kept: list[Any] = []
    min_range_sq = cfg.min_range_m * cfg.min_range_m
    max_range_sq = cfg.max_range_m * cfg.max_range_m

    for point in points:
        x = _get_attr(point, "x")
        y = _get_attr(point, "y")
        z = _get_attr(point, "z")
        doppler = _get_attr(point, "doppler")
        snr = _get_attr(point, "snr", -999.0)

        range_sq = x * x + y * y + z * z
        if range_sq < min_range_sq or range_sq > max_range_sq:
            continue

        # Reject detections behind radar and outside configured azimuth window.
        if y <= 0.0:
            continue
        azimuth = math.degrees(math.atan2(x, y))
        if abs(azimuth) > cfg.max_abs_azimuth_deg:
            continue

        if z < cfg.min_z_m or z > cfg.max_z_m:
            continue
        if abs(doppler) > cfg.max_abs_doppler_mps:
            continue

        # If SNR is unavailable (0.0 default from parser), do not reject by SNR.
        if snr > 0.0 and snr < cfg.min_snr_db:
            continue

        kept.append(point)

    return kept
