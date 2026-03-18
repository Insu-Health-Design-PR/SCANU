"""Temporal buffer for Layer 1-compatible frame inputs."""

from __future__ import annotations

from collections import deque
from typing import Any

class FrameBuffer:
    """Keeps a fixed-size sliding window of recent Layer 1-compatible inputs."""

    def __init__(self, max_frames: int = 64) -> None:
        if max_frames <= 0:
            raise ValueError("max_frames must be > 0")
        self._frames: deque[Any] = deque(maxlen=max_frames)

    def append(self, frame: Any) -> None:
        self._frames.append(frame)

    def extend(self, frames: list[Any]) -> None:
        self._frames.extend(frames)

    def snapshot(self) -> tuple[Any, ...]:
        return tuple(self._frames)

    def clear(self) -> None:
        self._frames.clear()

    def __len__(self) -> int:
        return len(self._frames)
