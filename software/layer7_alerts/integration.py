"""Integration hook from Layer 6 outputs into Layer 7 pipeline."""

from __future__ import annotations

from dataclasses import asdict

from software.layer6_state_machine.models import ActionRequest, StateEvent, StateSnapshot

from .alert_manager import AlertManager
from .event_logger import EventLogger
from .models import AlertPayload


class L6ToL7Bridge:
    """Builds and stores Layer 7 alerts from Layer 6 outputs."""

    def __init__(self, *, manager: AlertManager | None = None, logger: EventLogger | None = None) -> None:
        self._manager = manager if manager is not None else AlertManager()
        self._logger = logger if logger is not None else EventLogger()

    @property
    def logger(self) -> EventLogger:
        return self._logger

    def ingest(
        self,
        state_event: StateEvent,
        *,
        snapshot: StateSnapshot | None = None,
        action_request: ActionRequest | None = None,
    ) -> AlertPayload:
        metadata: dict[str, object] = {}
        if action_request is not None:
            metadata["action_request"] = asdict(action_request)

        payload = self._manager.build(state_event, snapshot=snapshot, metadata=metadata)
        self._logger.append(payload)
        return payload
