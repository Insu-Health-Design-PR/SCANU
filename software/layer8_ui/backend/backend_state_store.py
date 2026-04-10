"""In-memory backend state store for Layer 8 API and streaming."""

from __future__ import annotations

from collections import deque
from typing import Any

from software.layer6_state_machine.models import StateSnapshot
from software.layer7_alerts.models import AlertPayload

from .status_models import ApiHealthResponse, ApiStatusResponse, alert_to_dict, snapshot_to_dict, to_utc_iso


class BackendStateStore:
    """Stores latest status plus alert history for Layer 8 backend contracts."""

    def __init__(self, *, max_alerts: int = 2000) -> None:
        self._latest_snapshot: StateSnapshot | None = None
        self._latest_alert: AlertPayload | None = None
        self._alerts: deque[AlertPayload] = deque(maxlen=max_alerts)
        self._updated_ms: float | None = None

    def update_status(self, snapshot: StateSnapshot, *, now_ms: float | None = None) -> None:
        self._latest_snapshot = snapshot
        self._updated_ms = now_ms

    def publish_alert(self, payload: AlertPayload) -> None:
        self._latest_alert = payload
        self._alerts.append(payload)

    def status_response(self) -> dict[str, Any]:
        if self._latest_snapshot is None:
            empty = ApiStatusResponse(
                state="UNKNOWN",
                dwell_ms=0.0,
                fused_score=0.0,
                confidence=0.0,
                health={"has_fault": False, "fault_code": None, "sensor_online_count": 0},
                active_radars=[],
                updated_at_utc=to_utc_iso(self._updated_ms),
                latest_alert=alert_to_dict(self._latest_alert) if self._latest_alert else None,
            )
            return {
                "state": empty.state,
                "dwell_ms": empty.dwell_ms,
                "fused_score": empty.fused_score,
                "confidence": empty.confidence,
                "health": empty.health,
                "active_radars": empty.active_radars,
                "updated_at_utc": empty.updated_at_utc,
                "latest_alert": empty.latest_alert,
            }

        snapshot_data = snapshot_to_dict(self._latest_snapshot)
        payload = ApiStatusResponse(
            state=snapshot_data["state"],
            dwell_ms=snapshot_data["dwell_ms"],
            fused_score=snapshot_data["fused_score"],
            confidence=snapshot_data["confidence"],
            health=snapshot_data["health"],
            active_radars=snapshot_data["active_radars"],
            updated_at_utc=to_utc_iso(self._updated_ms),
            latest_alert=alert_to_dict(self._latest_alert) if self._latest_alert else None,
        )
        return {
            "state": payload.state,
            "dwell_ms": payload.dwell_ms,
            "fused_score": payload.fused_score,
            "confidence": payload.confidence,
            "health": payload.health,
            "active_radars": payload.active_radars,
            "updated_at_utc": payload.updated_at_utc,
            "latest_alert": payload.latest_alert,
        }

    def recent_alerts(self, *, limit: int = 50) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        items = list(self._alerts)
        selected = list(reversed(items[-limit:]))
        return [alert_to_dict(item) for item in selected]

    def health_response(self) -> dict[str, Any]:
        if self._latest_snapshot is None:
            payload = ApiHealthResponse(
                healthy=False,
                has_fault=False,
                fault_code=None,
                sensor_online_count=0,
                state="UNKNOWN",
                updated_at_utc=to_utc_iso(self._updated_ms),
            )
            return {
                "healthy": payload.healthy,
                "has_fault": payload.has_fault,
                "fault_code": payload.fault_code,
                "sensor_online_count": payload.sensor_online_count,
                "state": payload.state,
                "updated_at_utc": payload.updated_at_utc,
            }

        health = dict(self._latest_snapshot.health)
        has_fault = bool(health.get("has_fault", False))
        sensor_online_count = int(health.get("sensor_online_count", 0))
        healthy = (not has_fault) and sensor_online_count > 0

        payload = ApiHealthResponse(
            healthy=healthy,
            has_fault=has_fault,
            fault_code=health.get("fault_code"),
            sensor_online_count=sensor_online_count,
            state=self._latest_snapshot.state.value,
            updated_at_utc=to_utc_iso(self._updated_ms),
        )
        return {
            "healthy": payload.healthy,
            "has_fault": payload.has_fault,
            "fault_code": payload.fault_code,
            "sensor_online_count": payload.sensor_online_count,
            "state": payload.state,
            "updated_at_utc": payload.updated_at_utc,
        }
