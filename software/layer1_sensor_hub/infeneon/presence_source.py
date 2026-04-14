"""Source adapters for 60 GHz presence radar data."""

from __future__ import annotations

import time
from typing import Protocol

from .presence_models import PresenceFrame


class PresenceProvider(Protocol):
    """Provider contract for a presence reading source."""

    def read_sample(self) -> tuple[float, float, float]:
        """Returns `(presence_raw, motion_raw, distance_m)` for one sample."""


class MockPresenceProvider:
    """Deterministic mock provider for development and smoke testing."""

    def __init__(self) -> None:
        self._counter = 0

    def read_sample(self) -> tuple[float, float, float]:
        self._counter += 1
        cycle = self._counter % 6
        if cycle in (0, 1):
            return (0.15, 0.10, 2.8)
        if cycle in (2, 3):
            return (0.55, 0.45, 1.9)
        return (0.85, 0.70, 1.2)


class PresenceSource:
    """Reads sequential presence frames from a provider."""

    def __init__(self, provider: PresenceProvider) -> None:
        self._provider = provider
        self._frame_number = 0

    def read_frame(self) -> PresenceFrame:
        self._frame_number += 1
        presence_raw, motion_raw, distance_m = self._provider.read_sample()
        return PresenceFrame(
            frame_number=self._frame_number,
            timestamp_ms=time.time() * 1000.0,
            presence_raw=float(presence_raw),
            motion_raw=float(motion_raw),
            distance_m=float(distance_m),
        )
