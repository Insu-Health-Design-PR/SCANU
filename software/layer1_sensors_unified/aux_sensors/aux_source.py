"""Orchestrator for auxiliary sensor serial ingestion."""

from __future__ import annotations

import time
from typing import Callable

from .aux_protocol import AuxProtocol
from .config import AuxHealthConfig
from .health_monitor import HealthMonitor
from .sensor_models import AuxFrame
from .serial_bridge import SerialBridge


class AuxSensorSource:
    """Reads serial lines, parses protocol, and yields typed frame messages."""

    def __init__(
        self,
        bridge: SerialBridge,
        protocol: AuxProtocol | None = None,
        health_config: AuxHealthConfig | None = None,
        time_fn: Callable[[], float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self._bridge = bridge
        self._protocol = protocol if protocol is not None else AuxProtocol()
        self._health_config = health_config if health_config is not None else AuxHealthConfig()
        self._health = HealthMonitor(self._health_config)
        self._time_fn = time_fn if time_fn is not None else time.time
        self._sleep_fn = sleep_fn if sleep_fn is not None else time.sleep

        self._frames = 0
        self._heartbeats = 0
        self._parse_errors = 0
        self._read_errors = 0
        self._invalid_messages = 0
        self._empty_lines = 0
        self._dropped_messages = 0
        self._lines_total = 0
        self._reconnect_count = 0
        self._reconnect_attempts = 0
        self._heartbeat_loss_count = 0
        self._last_heartbeat_ts: float | None = None
        self._heartbeat_loss_latched = False

    def connect(self) -> None:
        self._bridge.connect()

    def disconnect(self) -> None:
        self._bridge.disconnect()

    def read_once(self) -> AuxFrame | None:
        self._check_heartbeat_timeout()

        if not self._bridge.is_connected and not self._attempt_reconnect():
            self._dropped_messages += 1
            return None

        try:
            line = self._bridge.readline().decode("utf-8", errors="ignore")
        except Exception:
            self._read_errors += 1
            self._dropped_messages += 1
            self._safe_disconnect()
            self._attempt_reconnect()
            return None

        self._lines_total += 1
        if not line.strip():
            self._empty_lines += 1
            return None

        try:
            parsed = self._protocol.decode_line(line)
        except Exception:
            self._parse_errors += 1
            self._invalid_messages += 1
            self._dropped_messages += 1
            return None

        if parsed is None:
            self._invalid_messages += 1
            self._dropped_messages += 1
            return None

        self._health.update_rx()
        if parsed.kind == "heartbeat":
            self._heartbeats += 1
            self._last_heartbeat_ts = self._time_fn()
            self._heartbeat_loss_latched = False
            return None

        if parsed.kind == "frame":
            self._frames += 1
            return parsed.payload  # type: ignore[return-value]

        self._invalid_messages += 1
        self._dropped_messages += 1
        return None

    def stream_frames(self, max_frames: int = 0):
        count = 0
        while max_frames <= 0 or count < max_frames:
            frame = self.read_once()
            if frame is not None:
                count += 1
                yield frame
            else:
                self._sleep_fn(0.01)

    def get_stats(self) -> dict[str, float | int | bool | str]:
        health = self._health.status()
        drop_rate = float(self._dropped_messages / self._lines_total) if self._lines_total > 0 else 0.0
        return {
            "frames": self._frames,
            "heartbeats": self._heartbeats,
            "parse_errors": self._parse_errors,
            "read_errors": self._read_errors,
            "invalid_messages": self._invalid_messages,
            "empty_lines": self._empty_lines,
            "dropped_messages": self._dropped_messages,
            "lines_total": self._lines_total,
            "drop_rate": drop_rate,
            "reconnect_count": self._reconnect_count,
            "reconnect_attempts": self._reconnect_attempts,
            "heartbeat_loss_count": self._heartbeat_loss_count,
            "healthy": health.healthy,
            "last_rx_age_s": health.last_rx_age_s,
            "health_reason": health.reason,
        }

    def _attempt_reconnect(self) -> bool:
        self._reconnect_attempts += 1
        backoff = float(getattr(getattr(self._bridge, "config", object()), "reconnect_backoff_s", 1.0))

        if backoff > 0:
            self._sleep_fn(backoff)

        try:
            self._bridge.connect()
            self._reconnect_count += 1
            return True
        except Exception:
            return False

    def _safe_disconnect(self) -> None:
        try:
            self._bridge.disconnect()
        except Exception:
            pass

    def _check_heartbeat_timeout(self) -> None:
        if self._last_heartbeat_ts is None:
            return

        age = self._time_fn() - self._last_heartbeat_ts
        timeout = self._health_config.heartbeat_timeout_s

        if age > timeout and not self._heartbeat_loss_latched:
            self._heartbeat_loss_count += 1
            self._heartbeat_loss_latched = True
        elif age <= timeout:
            self._heartbeat_loss_latched = False
