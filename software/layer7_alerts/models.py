"""Typed contracts for Layer 7 alerting and event logging."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AlertLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ALERT = "ALERT"
    FAULT = "FAULT"


@dataclass(frozen=True, slots=True)
class AlertPayload:
    event_id: str
    timestamp_utc: str
    level: AlertLevel
    state: str
    message: str
    radar_id: str
    scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
