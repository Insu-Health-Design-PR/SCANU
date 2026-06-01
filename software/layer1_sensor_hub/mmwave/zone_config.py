"""Configurable zone detection and zone-crossing alerts for mmWave."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ZoneConfig:
    name: str
    range_min_m: float
    range_max_m: float
    angle_min_deg: float = -180.0
    angle_max_deg: float = 180.0
    color: tuple[int, int, int] = (50, 50, 220)
    label: str = ""

    def contains(self, range_m: float, angle_deg: float = 0.0) -> bool:
        if not (self.range_min_m <= range_m <= self.range_max_m):
            return False
        if not (self.angle_min_deg <= angle_deg <= self.angle_max_deg):
            return False
        return True


@dataclass
class ZoneAlert:
    zone_name: str
    track_id: str | None
    range_m: float
    snr: float
    confidence: float
    timestamp_ms: float
    event_type: str = "zone_entry"


@dataclass
class ZoneMonitor:
    zones: list[ZoneConfig] = field(default_factory=lambda: [
        ZoneConfig(name="weapon", range_min_m=1.17, range_max_m=1.95,
                   color=(50, 50, 220), label="W"),
    ])
    on_alert: Callable[[ZoneAlert], None] | None = None

    _previous_zone_map: dict[str, set[str]] = field(default_factory=dict)

    def check_frame(self, frame: Any, timestamp_ms: float) -> list[ZoneAlert]:
        alerts: list[ZoneAlert] = []
        current: dict[str, set[str]] = {}
        for zone in self.zones:
            current[zone.name] = set()
        prev = self._previous_zone_map

        for obj in getattr(frame, "objects", []):
            for zone in self.zones:
                if zone.contains(getattr(obj, "range_m", 0.0)):
                    tid = str(getattr(obj, "track_id", "")) or ""
                    current[zone.name].add(tid)
                    if tid not in prev.get(zone.name, set()):
                        alert = ZoneAlert(
                            zone_name=zone.name,
                            track_id=getattr(obj, "track_id", None),
                            range_m=getattr(obj, "range_m", 0.0),
                            snr=getattr(obj, "snr", 0.0),
                            confidence=getattr(obj, "confidence", 0.0),
                            timestamp_ms=timestamp_ms,
                            event_type="zone_entry",
                        )
                        alerts.append(alert)
                        if self.on_alert:
                            self.on_alert(alert)
        for zone in self.zones:
            for tid in prev.get(zone.name, set()):
                if tid not in current.get(zone.name, set()):
                    alert = ZoneAlert(
                        zone_name=zone.name,
                        track_id=tid or None,
                        range_m=0.0, snr=0.0, confidence=0.0,
                        timestamp_ms=timestamp_ms,
                        event_type="zone_exit",
                    )
                    alerts.append(alert)
                    if self.on_alert:
                        self.on_alert(alert)
        self._previous_zone_map = current
        return alerts
