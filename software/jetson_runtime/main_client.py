"""HTTP client used by Jetson serve mode to send data to Main."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from .config import JetsonRuntimeConfig


class MainClient:
    def __init__(self, config: JetsonRuntimeConfig, *, timeout_s: float = 3.0) -> None:
        self._config = config
        self._timeout_s = float(timeout_s)

    @property
    def available(self) -> bool:
        return bool(self._config.main_url)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.available:
            return {"ok": False, "error": "main_url_not_configured"}
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._config.main_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:
                raw = resp.read()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        if not raw:
            return {"ok": True}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": True, "raw": raw.decode("utf-8", errors="replace")}
        return parsed if isinstance(parsed, dict) else {"ok": True, "data": parsed}

    def register(self) -> dict[str, Any]:
        return self._post(
            "/api/jetsons/register",
            {
                "jetson_id": self._config.jetson_id,
                "mode": self._config.mode,
                "location": self._config.location,
                "sensors": self._config.sensors,
            },
        )

    def heartbeat(self, health: dict[str, Any]) -> dict[str, Any]:
        return self._post(
            f"/api/jetsons/{self._config.jetson_id}/heartbeat",
            {
                "jetson_id": self._config.jetson_id,
                "mode": self._config.mode,
                "health": health,
            },
        )

    def send_frame(self, bundle: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/api/jetsons/{self._config.jetson_id}/frames", bundle)
