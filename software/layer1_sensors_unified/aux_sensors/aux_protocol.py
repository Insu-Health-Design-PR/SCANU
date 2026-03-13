"""JSON line protocol parser for auxiliary sensor data."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from .sensor_models import AuxFrame, AuxHeartbeat, AuxReading


@dataclass(frozen=True, slots=True)
class ParsedMessage:
    """Protocol decode result wrapper."""

    kind: str
    payload: AuxFrame | AuxHeartbeat


class AuxProtocol:
    """Decode newline-delimited JSON messages into typed payloads."""

    def decode_line(self, line: str) -> ParsedMessage | None:
        text = line.strip()
        if not text:
            return None

        data = json.loads(text)
        msg_type = str(data.get("type", ""))
        now_ms = time.time() * 1000.0

        if msg_type == "heartbeat":
            heartbeat = AuxHeartbeat(
                device_id=str(data.get("device_id", "unknown")),
                fw_version=str(data.get("fw", "unknown")),
                uptime_ms=int(data.get("uptime_ms", 0)),
                ts_host_ms=now_ms,
            )
            return ParsedMessage(kind="heartbeat", payload=heartbeat)

        if msg_type == "reading":
            readings_raw = data.get("readings", [])
            readings = tuple(self._parse_reading(item) for item in readings_raw)
            frame = AuxFrame(
                frame_id=int(data.get("frame_id", 0)),
                ts_device_ms=float(data.get("ts_device_ms", 0.0)),
                ts_host_ms=now_ms,
                readings=readings,
                raw_line=text,
            )
            return ParsedMessage(kind="frame", payload=frame)

        return None

    def encode_command(self, command: dict[str, Any]) -> str:
        return json.dumps(command, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _parse_reading(item: Any) -> AuxReading:
        obj = item if isinstance(item, dict) else {}
        return AuxReading(
            sensor_id=str(obj.get("sensor_id", "unknown")),
            sensor_type=str(obj.get("sensor_type", "unknown")),
            value=float(obj.get("value", 0.0)),
            unit=str(obj.get("unit", "raw")),
            quality=float(obj.get("quality", 1.0)),
        )
