"""Alert payload builder for Layer 7."""

from __future__ import annotations

from dataclasses import dataclass

from software.layer6_state_machine import StateEvent, SystemState


@dataclass(frozen=True, slots=True)
class AlertPayload:
    """Notification envelope consumed by output adapters."""

    level: str
    message: str
    metadata: dict[str, str]


class AlertManager:
    """Generates normalized alert payloads from state events."""

    def build_payload(self, event: StateEvent) -> AlertPayload:
        level = {
            SystemState.ALERT: "CRITICAL",
            SystemState.FAULT: "ERROR",
        }.get(event.current_state, "INFO")
        message = f"{event.previous_state.value} -> {event.current_state.value}: {event.reason}"
        metadata = {
            "previous_state": event.previous_state.value,
            "current_state": event.current_state.value,
        }
        return AlertPayload(level=level, message=message, metadata=metadata)
