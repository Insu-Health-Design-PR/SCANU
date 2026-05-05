"""Append-only event logger for Layer 7 alert payloads — with JSONL persistence."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from .models import AlertLevel, AlertPayload


class EventLogger:
    """In-memory append-only logger with JSONL file persistence."""

    def __init__(self, max_events: int = 5000, file_path: Optional[str | Path] = None) -> None:
        self._events: deque[AlertPayload] = deque(maxlen=max_events)
        self._file_path = Path(file_path) if file_path else None
        if self._file_path and self._file_path.is_file():
            self._load_from_file()

    def append(self, payload: AlertPayload) -> None:
        self._events.append(payload)
        if self._file_path:
            self._append_to_file(payload)

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

    # ── file persistence ────────────────────────────────────────────

    def _append_to_file(self, payload: AlertPayload) -> None:
        assert self._file_path is not None
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(asdict(payload), default=str)
            with open(self._file_path, "a") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def _load_from_file(self) -> None:
        assert self._file_path is not None
        try:
            lines = self._file_path.read_text().strip().splitlines()
            for line in lines[-5000:]:
                try:
                    data = json.loads(line)
                    payload = AlertPayload(
                        event_id=data.get("event_id", ""),
                        timestamp_utc=data.get("timestamp_utc", ""),
                        level=AlertLevel(data.get("level", "INFO")),
                        state=data.get("state", "IDLE"),
                        message=data.get("message", ""),
                        radar_id=data.get("radar_id", "radar_main"),
                        scores=data.get("scores", {}),
                        metadata=data.get("metadata", {}),
                    )
                    self._events.append(payload)
                except (KeyError, TypeError, json.JSONDecodeError):
                    continue
        except OSError:
            pass
