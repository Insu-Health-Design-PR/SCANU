"""Normalized mmWave frame contracts for Layer 8 and fusion.

The UART/TLV capture path has historically written frames in a few slightly
different shapes. This module gives the UI and downstream layers one stable
JSON contract without forcing all capture scripts to change at once.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass
class NormalizedMmwaveObject:
    x: float
    y: float
    z: float = 0.0
    range_m: float = 0.0
    velocity_mps: float = 0.0
    snr: float = 0.0
    confidence: float = 0.0
    track_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "range_m": self.range_m,
            "velocity_mps": self.velocity_mps,
            "snr": self.snr,
            "confidence": self.confidence,
        }
        if self.track_id is not None:
            out["track_id"] = self.track_id
        return out


@dataclass
class NormalizedMmwaveFrame:
    frame_id: int
    timestamp_ms: float
    radar_id: str = "radar_main"
    objects: list[NormalizedMmwaveObject] = field(default_factory=list)
    source: str = "uart_tlv"
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp_ms": self.timestamp_ms,
            "radar_id": self.radar_id,
            "source": self.source,
            "objects": [obj.to_dict() for obj in self.objects],
            "object_count": len(self.objects),
        }


def _float_value(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except (TypeError, ValueError):
        return default


def _int_value(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_mmwave_object(raw: Any) -> NormalizedMmwaveObject | None:
    """Coerce one point/object into the stable object contract."""

    if not isinstance(raw, dict):
        return None

    x = _float_value(raw.get("x", raw.get("x_m", raw.get("pos_x", 0.0))))
    y = _float_value(raw.get("y", raw.get("y_m", raw.get("pos_y", 0.0))))
    z = _float_value(raw.get("z", raw.get("z_m", raw.get("pos_z", 0.0))))

    range_m = _float_value(raw.get("range_m", raw.get("range", raw.get("distance_m", 0.0))))
    if range_m <= 0.0:
        range_m = math.sqrt(x * x + y * y + z * z)

    velocity = _float_value(raw.get("velocity_mps", raw.get("velocity", raw.get("doppler", 0.0))))
    snr = _float_value(raw.get("snr", raw.get("snr_db", 0.0)))
    confidence = _float_value(raw.get("confidence", raw.get("score", 0.0)))
    if confidence <= 0.0 and snr > 0.0:
        confidence = max(0.0, min(1.0, snr / 35.0))

    track_id = raw.get("track_id", raw.get("id"))
    track_id_s = str(track_id) if track_id is not None and str(track_id).strip() else None

    return NormalizedMmwaveObject(
        x=x,
        y=y,
        z=z,
        range_m=range_m,
        velocity_mps=velocity,
        snr=snr,
        confidence=confidence,
        track_id=track_id_s,
    )


def normalize_mmwave_frame(raw: Any, *, radar_id: str = "radar_main", fallback_frame_id: int = 0) -> NormalizedMmwaveFrame:
    """Normalize one raw mmWave frame.

    Empty or malformed frames still produce a valid frame with zero objects.
    """

    if not isinstance(raw, dict):
        raw = {}

    frame_id = _int_value(
        raw.get("frame_id", raw.get("frame_number", raw.get("frame"))),
        default=fallback_frame_id,
    )
    timestamp_ms = _float_value(raw.get("timestamp_ms", raw.get("ts_ms")), default=time.time() * 1000.0)

    raw_points = raw.get("objects")
    if raw_points is None:
        raw_points = raw.get("points")
    if not isinstance(raw_points, list):
        raw_points = []

    objects = [obj for obj in (normalize_mmwave_object(p) for p in raw_points) if obj is not None]
    return NormalizedMmwaveFrame(
        frame_id=frame_id,
        timestamp_ms=timestamp_ms,
        radar_id=str(raw.get("radar_id") or radar_id),
        objects=objects,
        source=str(raw.get("source") or "uart_tlv"),
        raw=dict(raw),
    )


def normalize_mmwave_frames(raw_frames: Iterable[Any], *, radar_id: str = "radar_main") -> list[NormalizedMmwaveFrame]:
    return [
        normalize_mmwave_frame(raw, radar_id=radar_id, fallback_frame_id=i + 1)
        for i, raw in enumerate(raw_frames)
    ]


def load_normalized_mmwave_frames(path: str | Path, *, radar_id: str = "radar_main") -> list[NormalizedMmwaveFrame]:
    p = Path(path)
    try:
        payload = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, dict):
        if isinstance(payload.get("frames"), list):
            payload = payload["frames"]
        else:
            payload = [payload]
    if not isinstance(payload, list):
        return []
    return normalize_mmwave_frames(payload, radar_id=radar_id)


def dump_normalized_mmwave_frames(frames: Iterable[NormalizedMmwaveFrame], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps([frame.to_dict() for frame in frames], indent=2))
    tmp.replace(p)
