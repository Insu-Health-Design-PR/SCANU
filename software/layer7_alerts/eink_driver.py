"""Minimal E-Ink adapter for Layer 7."""

from __future__ import annotations

from .alert_manager import AlertPayload


class EInkDriver:
    """Formats alert payloads for display rendering."""

    def render(self, payload: AlertPayload) -> str:
        return f"[{payload.level}] {payload.message}"
