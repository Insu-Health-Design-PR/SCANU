"""Thermal camera source adapters."""

from __future__ import annotations

import time
from typing import Protocol

import numpy as np

from .camera_models import ThermalFrame


class FrameProvider(Protocol):
    """Protocol for pluggable thermal frame providers."""

    def read_temperature_map(self) -> np.ndarray:
        """Returns a 2D temperature map in Celsius."""


class MockLeptonProvider:
    """Deterministic mock frame provider for development and smoke tests."""

    def __init__(self, height: int = 60, width: int = 80) -> None:
        self._h = height
        self._w = width
        self._counter = 0

    def read_temperature_map(self) -> np.ndarray:
        self._counter += 1
        base = np.full((self._h, self._w), 24.5, dtype=np.float32)
        y = (self._counter * 3) % self._h
        x = (self._counter * 5) % self._w
        base[max(0, y - 1):min(self._h, y + 2), max(0, x - 1):min(self._w, x + 2)] = 31.0
        return base


class ThermalCameraSource:
    """Reads sequential thermal frames from an underlying provider."""

    def __init__(self, provider: FrameProvider) -> None:
        self._provider = provider
        self._frame_number = 0

    def read_frame(self) -> ThermalFrame:
        self._frame_number += 1
        temp_map = self._provider.read_temperature_map().astype(np.float32)
        return ThermalFrame(
            frame_number=self._frame_number,
            timestamp_ms=time.time() * 1000.0,
            temperature_c=temp_map,
        )
