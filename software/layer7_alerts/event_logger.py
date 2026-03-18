"""In-memory event logger for Layer 7."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .alert_manager import AlertPayload


@dataclass(frozen=True, slots=True)
class EventRecord:
    """Logged alert record."""

    ts_iso: str
    level: str
    message: str


class EventLogger:
    """Stores alert history in memory for smoke tests and integration."""

    def __init__(self) -> None:
        self.records: list[EventRecord] = []

    def append(self, payload: AlertPayload) -> EventRecord:
        record = EventRecord(
            ts_iso=datetime.now(timezone.utc).isoformat(),
            level=payload.level,
            message=payload.message,
        )
        self.records.append(record)
        return record
