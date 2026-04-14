"""Persistence for Layer 8 UI preferences."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


class UiPrefsStore:
    """Lightweight JSON persistence for dashboard UI preferences.

    This is intentionally simple and file-based so it works in local/dev
    environments without additional infrastructure.
    """

    def __init__(self, path: Path | None = None) -> None:
        default_path = Path(__file__).resolve().parent / "ui_prefs.json"
        self._path = path or default_path
        self._lock = Lock()

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self._path.exists():
                return {}
            try:
                raw = self._path.read_text(encoding="utf-8")
                payload = json.loads(raw)
                if isinstance(payload, dict):
                    return payload
            except Exception:
                return {}
        return {}

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
            return payload
