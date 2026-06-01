"""Tests for ZoneConfig and ZoneMonitor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from layer1_sensor_hub.mmwave.zone_config import ZoneConfig, ZoneAlert, ZoneMonitor


@dataclass
class FakeObject:
    x: float = 0.0
    y: float = 0.0
    range_m: float = 1.5
    snr: float = 15.0
    confidence: float = 0.8
    track_id: str | None = "t1"
    velocity_mps: float = 0.0


@dataclass
class FakeFrame:
    frame_id: int = 1
    objects: list = None  # type: ignore


def test_zone_config_contains() -> None:
    z = ZoneConfig(name="weapon", range_min_m=1.0, range_max_m=2.0)
    assert z.contains(1.5) is True
    assert z.contains(0.9) is False
    assert z.contains(2.1) is False
    assert z.contains(1.5, 45.0) is True


def test_zone_config_with_angle() -> None:
    z = ZoneConfig(name="front", range_min_m=0.0, range_max_m=5.0, angle_min_deg=-30, angle_max_deg=30)
    assert z.contains(2.0, 0.0) is True
    assert z.contains(2.0, 45.0) is False


def test_zone_monitor_entry_alert() -> None:
    alerts: list[ZoneAlert] = []
    def cb(a: ZoneAlert) -> None:
        alerts.append(a)

    monitor = ZoneMonitor(on_alert=cb)
    frame = FakeFrame(objects=[FakeObject(range_m=1.5, track_id="t1")])

    result = monitor.check_frame(frame, 1000.0)
    assert len(result) == 1
    assert result[0].event_type == "zone_entry"
    assert result[0].zone_name == "weapon"
    assert result[0].track_id == "t1"
    assert len(alerts) == 1


def test_zone_monitor_no_duplicate_entry() -> None:
    monitor = ZoneMonitor()
    frame = FakeFrame(objects=[FakeObject(range_m=1.5, track_id="t1")])

    r1 = monitor.check_frame(frame, 1000.0)
    r2 = monitor.check_frame(frame, 1100.0)
    assert len(r1) == 1
    assert len(r2) == 0


def test_zone_monitor_exit_alert() -> None:
    alerts: list[ZoneAlert] = []
    def cb(a: ZoneAlert) -> None:
        alerts.append(a)

    monitor = ZoneMonitor(on_alert=cb)
    obj_in = FakeObject(range_m=1.5, track_id="t1")
    obj_out = FakeObject(range_m=3.0, track_id="t1")

    monitor.check_frame(FakeFrame(objects=[obj_in]), 1000.0)
    result = monitor.check_frame(FakeFrame(objects=[obj_out]), 2000.0)

    assert len(result) == 1
    assert result[0].event_type == "zone_exit"
    assert result[0].zone_name == "weapon"
    assert result[0].track_id == "t1"
    assert len(alerts) == 2  # entry + exit


def test_zone_monitor_outside_zone_no_alert() -> None:
    monitor = ZoneMonitor()
    frame = FakeFrame(objects=[FakeObject(range_m=3.0, track_id="t1")])
    result = monitor.check_frame(frame, 1000.0)
    assert len(result) == 0


def test_zone_monitor_custom_zones() -> None:
    custom = [ZoneConfig(name="danger", range_min_m=2.0, range_max_m=3.0)]
    monitor = ZoneMonitor(zones=custom)
    frame = FakeFrame(objects=[FakeObject(range_m=2.5, track_id="t1")])
    result = monitor.check_frame(frame, 1000.0)
    assert len(result) == 1
    assert result[0].zone_name == "danger"
