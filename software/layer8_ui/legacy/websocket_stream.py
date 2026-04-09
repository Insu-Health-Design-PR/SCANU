"""Websocket event encoder for Layer 8."""

from __future__ import annotations

import json
from typing import Any


class WebSocketStream:
    """Encodes event envelopes as compact JSON strings."""

    @staticmethod
    def encode(event_type: str, payload: Any) -> str:
        body = {"event_type": event_type, "payload": payload}
        return json.dumps(body, separators=(",", ":"), sort_keys=True)
