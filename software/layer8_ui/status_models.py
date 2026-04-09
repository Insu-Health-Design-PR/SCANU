"""Typed API-facing contracts and serialization helpers for Layer 8."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from software.layer6_state_machine.models import StateSnapshot
from software.layer7_alerts.models import AlertPayload


@dataclass(frozen=True, slots=True)
class ApiStatusResponse:
    state: str
    dwell_ms: float
    fused_score: float
    confidence: float
    health: dict[str, Any]
    active_radars: list[str]
    updated_at_utc: str | None
    latest_alert: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class ApiHealthResponse:
    healthy: bool
    has_fault: bool
    fault_code: str | None
    sensor_online_count: int
    state: str
    updated_at_utc: str | None


def to_utc_iso(timestamp_ms: float | None) -> str | None:
    if timestamp_ms is None:
        return None
    dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC)
    return dt.isoformat().replace("+00:00", "Z")


def snapshot_to_dict(snapshot: StateSnapshot) -> dict[str, Any]:
    return {
        "state": snapshot.state.value,
        "dwell_ms": float(snapshot.dwell_ms),
        "fused_score": float(snapshot.fused_score),
        "confidence": float(snapshot.confidence),
        "health": dict(snapshot.health),
        "active_radars": list(snapshot.active_radars),
    }


def alert_to_dict(alert: AlertPayload) -> dict[str, Any]:
    return {
        "event_id": alert.event_id,
        "timestamp_utc": alert.timestamp_utc,
        "level": alert.level.value,
        "state": alert.state,
        "message": alert.message,
        "radar_id": alert.radar_id,
        "scores": dict(alert.scores),
        "metadata": dict(alert.metadata),
    }
