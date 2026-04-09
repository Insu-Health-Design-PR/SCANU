"""WebSocket event encoding contracts for Layer 8."""

from __future__ import annotations

from typing import Any

from software.layer6_state_machine.models import StateSnapshot
from software.layer7_alerts.models import AlertPayload

from .status_models import alert_to_dict, snapshot_to_dict


class WebSocketStream:
    """Encodes strongly-typed websocket event payloads."""

    @staticmethod
    def encode_status(snapshot: StateSnapshot) -> dict[str, Any]:
        return {
            "event_type": "status_update",
            "payload": snapshot_to_dict(snapshot),
        }

    @staticmethod
    def encode_alert(payload: AlertPayload) -> dict[str, Any]:
        return {
            "event_type": "alert_event",
            "payload": alert_to_dict(payload),
        }

    @staticmethod
    def encode_sensor_fault(details: dict[str, Any]) -> dict[str, Any]:
        return {
            "event_type": "sensor_fault",
            "payload": dict(details),
        }

    @staticmethod
    def encode_heartbeat(ts_utc: str) -> dict[str, Any]:
        return {
            "event_type": "heartbeat",
            "payload": {"timestamp_utc": ts_utc},
        }
