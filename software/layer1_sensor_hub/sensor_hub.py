"""Unified Layer 1 sensor hub for mmWave, Infeneon 60G, and thermal."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .infeneon import PresenceSource

if TYPE_CHECKING:
    from .thermal import ThermalCameraSource


@dataclass(frozen=True, slots=True)
class HubFrame:
    """Single synchronized read across all enabled sensor sources."""

    frame_number: int
    timestamp_ms: float
    mmwave_frame: Optional[object]
    presence_frame: Optional[object]
    thermal_frame_bgr: Optional[object]


class MultiSensorHub:
    """Orchestrates readout of all Layer 1 sensors from one entrypoint."""

    def __init__(
        self,
        *,
        mmwave_source: Optional[object] = None,
        mmwave_parser: Optional[object] = None,
        presence_source: Optional[PresenceSource] = None,
        thermal_source: Optional["ThermalCameraSource"] = None,
    ) -> None:
        self._mmwave_source = mmwave_source
        self._mmwave_parser = mmwave_parser
        self._presence_source = presence_source
        self._thermal_source = thermal_source
        self._frame_number = 0

    def read_frame(self, *, mmwave_timeout_ms: int = 200) -> HubFrame:
        """Read one frame from each enabled source."""

        self._frame_number += 1
        now_ms = time.time() * 1000.0

        mmwave_frame = None
        if self._mmwave_source is not None:
            raw = self._mmwave_source.read_frame(timeout_ms=mmwave_timeout_ms)
            if raw is not None:
                mmwave_frame = self._mmwave_parser.parse(raw) if self._mmwave_parser is not None else raw

        presence_frame = self._presence_source.read_frame() if self._presence_source is not None else None
        thermal_frame = self._thermal_source.read_colormap_bgr() if self._thermal_source is not None else None

        return HubFrame(
            frame_number=self._frame_number,
            timestamp_ms=now_ms,
            mmwave_frame=mmwave_frame,
            presence_frame=presence_frame,
            thermal_frame_bgr=thermal_frame,
        )

    def close(self) -> None:
        """Close optional providers that expose cleanup methods."""

        if self._thermal_source is not None:
            close_fn = getattr(self._thermal_source, "close", None)
            if callable(close_fn):
                close_fn()

        if self._presence_source is not None:
            provider = getattr(self._presence_source, "_provider", None)
            close_fn = getattr(provider, "close", None)
            if callable(close_fn):
                close_fn()
