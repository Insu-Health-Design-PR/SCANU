"""Temporal buffer for raw radar frames."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RadarFrame:
    """Raw frame payload from Layer 1."""

    frame_number: int
    timestamp_ms: float
    payload: bytes


class FrameBuffer:
    """Keeps a fixed-size sliding window of recent frames."""

    def __init__(self, max_frames: int = 64) -> None:
        if max_frames <= 0:
            raise ValueError("max_frames must be > 0")
        self._frames: deque[RadarFrame] = deque(maxlen=max_frames)

    def append(self, frame: RadarFrame) -> None:
        self._frames.append(frame)

    def extend(self, frames: list[RadarFrame]) -> None:
        self._frames.extend(frames)

    def snapshot(self) -> tuple[RadarFrame, ...]:
        return tuple(self._frames)

    def clear(self) -> None:
        self._frames.clear()

    def __len__(self) -> int:
        return len(self._frames)
