"""Layer 7 alert builder from Layer 6 state transitions."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from software.layer6_state_machine.models import StateEvent, StateSnapshot, SystemState

from .models import AlertLevel, AlertPayload


class AlertManager:
    """Maps Layer 6 state events to normalized Layer 7 alert payloads."""

    _STATE_TO_LEVEL: dict[SystemState, AlertLevel] = {
        SystemState.IDLE: AlertLevel.INFO,
        SystemState.TRIGGERED: AlertLevel.WARNING,
        SystemState.SCANNING: AlertLevel.WARNING,
        SystemState.ANOMALY_DETECTED: AlertLevel.ALERT,
        SystemState.FAULT: AlertLevel.FAULT,
    }

    def build(
        self,
        state_event: StateEvent,
        *,
        snapshot: StateSnapshot | None = None,
        metadata: dict[str, object] | None = None,
    ) -> AlertPayload:
        level = self._STATE_TO_LEVEL[state_event.current_state]
        timestamp_utc = _to_utc_iso(state_event.timestamp_ms)

        payload_metadata: dict[str, object] = {}
        if snapshot is not None:
            payload_metadata["snapshot"] = {
                "state": str(snapshot.state),
                "dwell_ms": snapshot.dwell_ms,
                "health": dict(snapshot.health),
                "active_radars": list(snapshot.active_radars),
            }
        if metadata:
            payload_metadata.update(metadata)

        return AlertPayload(
            event_id=f"evt_{uuid4().hex}",
            timestamp_utc=timestamp_utc,
            level=level,
            state=state_event.current_state.value,
            message=_build_message(state_event),
            radar_id=state_event.radar_id,
            scores=dict(state_event.scores),
            metadata=payload_metadata,
        )


def _build_message(event: StateEvent) -> str:
    previous_state = event.previous_state.value
    current_state = event.current_state.value
    return f"{previous_state} -> {current_state} ({event.reason})"


def _to_utc_iso(timestamp_ms: float) -> str:
    dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")
