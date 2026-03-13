"""Typed data contracts for auxiliary sensors."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AuxReading:
    """One normalized sensor reading from an auxiliary source."""

    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    quality: float = 1.0


@dataclass(frozen=True, slots=True)
class AuxFrame:
    """A frame-level bundle of auxiliary readings."""

    frame_id: int
    ts_device_ms: float
    ts_host_ms: float
    readings: tuple[AuxReading, ...] = field(default_factory=tuple)
    raw_line: str = ""


@dataclass(frozen=True, slots=True)
class AuxHeartbeat:
    """Heartbeat sent by the device to monitor link health."""

    device_id: str
    fw_version: str
    uptime_ms: int
    ts_host_ms: float
