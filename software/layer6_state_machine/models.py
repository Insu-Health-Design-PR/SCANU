"""Typed contracts for Layer 6 state and control plane."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SystemState(str, Enum):
    IDLE = "IDLE"
    TRIGGERED = "TRIGGERED"
    SCANNING = "SCANNING"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    FAULT = "FAULT"


@dataclass(frozen=True, slots=True)
class StateMachineConfig:
    trigger_threshold: float = 0.35
    scan_threshold: float = 0.45
    anomaly_threshold: float = 0.75
    anomaly_exit_threshold: float = 0.55
    minimum_confidence: float = 0.35
    trigger_enter_frames: int = 2
    scan_min_frames: int = 3
    anomaly_enter_frames: int = 2
    anomaly_exit_frames: int = 3


@dataclass(frozen=True, slots=True)
class FusionInputContract:
    frame_number: int
    timestamp_ms: float
    radar_id: str
    fused_score: float
    confidence: float
    trigger_score: float
    anomaly_score: float
    source_mode: str = "provisional_l1_l2"
    evidence: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SystemHealth:
    has_fault: bool = False
    fault_code: Optional[str] = None
    fault_clear_requested: bool = False
    sensor_online_count: int = 0


@dataclass(frozen=True, slots=True)
class StateEvent:
    previous_state: SystemState
    current_state: SystemState
    reason: str
    frame_number: int
    timestamp_ms: float
    radar_id: str
    scores: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StateSnapshot:
    state: SystemState
    dwell_ms: float
    fused_score: float
    confidence: float
    health: dict[str, object] = field(default_factory=dict)
    active_radars: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RadarRuntimeSpec:
    radar_id: str
    config_port: Optional[str] = None
    data_port: Optional[str] = None
    default_config_path: Optional[str] = None


@dataclass(frozen=True, slots=True)
class SensorStatus:
    radar_id: str
    connected: bool
    configured: bool
    streaming: bool
    fault_code: Optional[str]
    last_seen_ms: Optional[float]
    config_port: Optional[str] = None
    data_port: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ControlResult:
    radar_id: str
    action: str
    success: bool
    message: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ActionRequest:
    radar_id: str
    action: str
    reason: str
    manual_required: bool = False
    params: dict[str, object] = field(default_factory=dict)
