"""Configuration for Layer 1 auxiliary sensor ingestion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuxSerialConfig:
    """Runtime serial configuration for ESP32 auxiliary sensor bridge."""

    port: str = "/dev/ttyUSB0"
    baudrate: int = 115200
    timeout_s: float = 0.2
    reconnect_backoff_s: float = 1.0
    max_line_bytes: int = 4096


@dataclass(frozen=True, slots=True)
class AuxHealthConfig:
    """Health and watchdog settings for auxiliary sensor ingestion."""

    heartbeat_timeout_s: float = 5.0
    stream_timeout_s: float = 2.0
