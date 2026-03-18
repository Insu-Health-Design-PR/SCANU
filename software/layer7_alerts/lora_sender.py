"""Minimal LoRa sender serializer for Layer 7."""

from __future__ import annotations

import json

from .alert_manager import AlertPayload


class LoRaSender:
    """Serializes alert payloads into compact JSON bytes."""

    def serialize(self, payload: AlertPayload) -> bytes:
        body = {
            "level": payload.level,
            "message": payload.message,
            "metadata": payload.metadata,
        }
        return json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
