"""Typed contracts for thermal camera acquisition and processing."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ThermalFrame:
    """Raw thermal frame with temperature map in Celsius."""

    frame_number: int
    timestamp_ms: float
    temperature_c: np.ndarray


@dataclass(frozen=True, slots=True)
class ThermalFeatures:
    """Lightweight thermal features for downstream fusion."""

    frame_number: int
    timestamp_ms: float
    max_temp_c: float
    mean_temp_c: float
    hotspot_ratio: float
    presence_score: float
