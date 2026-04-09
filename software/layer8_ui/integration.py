"""Integration adapter from Layer 6/7 outputs into Layer 8 backend and stream."""

from __future__ import annotations

import time

from software.layer6_state_machine.models import ActionRequest, StateSnapshot
from software.layer7_alerts.models import AlertPayload

from .backend_state_store import BackendStateStore
from .publisher import BackendPublisher
from .status_models import to_utc_iso
from .websocket_stream import WebSocketStream


class L6L7ToL8Bridge:
    """Forwards orchestrator outputs to Layer 8 store and websocket publisher."""

    def __init__(self, *, store: BackendStateStore | None = None, publisher: BackendPublisher | None = None) -> None:
        self._store = store if store is not None else BackendStateStore()
        self._publisher = publisher if publisher is not None else BackendPublisher()

    @property
    def store(self) -> BackendStateStore:
        return self._store

    @property
    def publisher(self) -> BackendPublisher:
        return self._publisher

    def ingest(
        self,
        *,
        snapshot: StateSnapshot,
        alert: AlertPayload | None = None,
        action_request: ActionRequest | None = None,
        now_ms: float | None = None,
    ) -> None:
        ts_ms = float(now_ms if now_ms is not None else time.time() * 1000.0)
        self._store.update_status(snapshot, now_ms=ts_ms)
        self._publisher.publish(WebSocketStream.encode_status(snapshot))

        if alert is not None:
            self._store.publish_alert(alert)
            self._publisher.publish(WebSocketStream.encode_alert(alert))

        if snapshot.health.get("has_fault", False):
            payload = {
                "radars": list(snapshot.active_radars),
                "fault_code": snapshot.health.get("fault_code"),
            }
            if action_request is not None:
                payload["action_request"] = {
                    "action": action_request.action,
                    "reason": action_request.reason,
                    "manual_required": action_request.manual_required,
                }
            self._publisher.publish(WebSocketStream.encode_sensor_fault(payload))

        self._publisher.publish(WebSocketStream.encode_heartbeat(to_utc_iso(ts_ms) or ""))
