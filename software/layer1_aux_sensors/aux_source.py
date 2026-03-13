"""Orchestrator for auxiliary sensor serial ingestion."""

from __future__ import annotations

import time

from .aux_protocol import AuxProtocol
from .health_monitor import HealthMonitor
from .sensor_models import AuxFrame
from .serial_bridge import SerialBridge


class AuxSensorSource:
    """Reads serial lines, parses protocol, and yields typed frame messages."""

    def __init__(self, bridge: SerialBridge, protocol: AuxProtocol | None = None) -> None:
        self._bridge = bridge
        self._protocol = protocol if protocol is not None else AuxProtocol()
        self._health = HealthMonitor()
        self._frames = 0
        self._parse_errors = 0

    def connect(self) -> None:
        self._bridge.connect()

    def disconnect(self) -> None:
        self._bridge.disconnect()

    def read_once(self) -> AuxFrame | None:
        line = self._bridge.readline().decode("utf-8", errors="ignore")
        if not line.strip():
            return None

        try:
            parsed = self._protocol.decode_line(line)
        except Exception:
            self._parse_errors += 1
            return None

        if parsed is None:
            return None

        self._health.update_rx()
        if parsed.kind == "frame":
            self._frames += 1
            return parsed.payload  # type: ignore[return-value]
        return None

    def stream_frames(self, max_frames: int = 0):
        count = 0
        while max_frames <= 0 or count < max_frames:
            frame = self.read_once()
            if frame is not None:
                count += 1
                yield frame
            else:
                time.sleep(0.01)

    def get_stats(self) -> dict[str, float | int | bool | str]:
        health = self._health.status()
        return {
            "frames": self._frames,
            "parse_errors": self._parse_errors,
            "healthy": health.healthy,
            "last_rx_age_s": health.last_rx_age_s,
            "health_reason": health.reason,
        }
