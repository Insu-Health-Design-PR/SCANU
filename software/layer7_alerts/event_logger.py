"""Append-only event logger for Layer 7 alert payloads."""

from __future__ import annotations

from collections import deque

from .models import AlertLevel, AlertPayload


class EventLogger:
    """In-memory append-only logger with simple query helpers."""

    def __init__(self, max_events: int = 5000) -> None:
        self._events: deque[AlertPayload] = deque(maxlen=max_events)

    def append(self, payload: AlertPayload) -> None:
        self._events.append(payload)

    def recent(self, limit: int = 50) -> list[AlertPayload]:
        if limit <= 0:
            return []
        items = list(self._events)
        return list(reversed(items[-limit:]))

    def by_level(self, level: AlertLevel, limit: int = 50) -> list[AlertPayload]:
        if limit <= 0:
            return []
        matches = [item for item in self._events if item.level == level]
        return list(reversed(matches[-limit:]))

    def count(self) -> int:
        return len(self._events)
