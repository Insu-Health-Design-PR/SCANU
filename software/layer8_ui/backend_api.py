"""Backend API facade for Layer 8."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from software.layer6_state_machine import SystemState
from software.layer7_alerts import AlertPayload


@dataclass(slots=True)
class SystemStatus:
    """Current service status exposed to consumers."""

    state: str
    last_score: float
    healthy: bool


class BackendAPI:
    """Stores current status and latest alert for API consumers."""

    def __init__(self) -> None:
        self._status = SystemStatus(state=SystemState.IDLE.value, last_score=0.0, healthy=True)
        self._last_alert: AlertPayload | None = None

    def update_status(self, state: SystemState, last_score: float, healthy: bool) -> None:
        self._status = SystemStatus(state=state.value, last_score=float(last_score), healthy=healthy)

    def publish_alert(self, payload: AlertPayload) -> None:
        self._last_alert = payload

    def get_status(self) -> dict:
        data = asdict(self._status)
        if self._last_alert is not None:
            data["last_alert"] = {
                "level": self._last_alert.level,
                "message": self._last_alert.message,
                "metadata": self._last_alert.metadata,
            }
        return data
