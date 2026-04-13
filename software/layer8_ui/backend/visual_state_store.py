"""In-memory visual payload store for Layer 8 operator UI."""

from __future__ import annotations

import threading
from typing import Any


class VisualStateStore:
    """Keeps only the latest visual payload to serve REST + WS clients."""

    def __init__(self) -> None:
        self._latest: dict[str, Any] | None = None
        self._lock = threading.RLock()

    def update(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._latest = dict(payload)

    def latest(self) -> dict[str, Any]:
        with self._lock:
            if self._latest is None:
                return {
                    "timestamp_ms": None,
                    "source_mode": "none",
                    "rgb_jpeg_b64": None,
                    "thermal_jpeg_b64": None,
                    "point_cloud": [],
                    "presence": None,
                    "meta": {"ready": False},
                }
            return dict(self._latest)
