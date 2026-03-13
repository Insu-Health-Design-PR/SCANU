"""Health watchdog for auxiliary sensor ingestion."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .config import AuxHealthConfig


@dataclass(frozen=True, slots=True)
class HealthStatus:
    """Current health snapshot."""

    healthy: bool
    last_rx_age_s: float
    reason: str


class HealthMonitor:
    """Tracks last successful RX timestamp and computes health status."""

    def __init__(self, config: AuxHealthConfig | None = None) -> None:
        self._config = config if config is not None else AuxHealthConfig()
        self._last_rx_ts: float | None = None

    def update_rx(self) -> None:
        self._last_rx_ts = time.time()

    def status(self) -> HealthStatus:
        now = time.time()
        if self._last_rx_ts is None:
            return HealthStatus(healthy=False, last_rx_age_s=float("inf"), reason="no data received yet")

        age = now - self._last_rx_ts
        healthy = age <= self._config.stream_timeout_s
        reason = "ok" if healthy else "stream timeout"
        return HealthStatus(healthy=healthy, last_rx_age_s=age, reason=reason)
