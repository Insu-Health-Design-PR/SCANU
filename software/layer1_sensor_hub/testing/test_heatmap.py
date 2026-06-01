"""Tests for HeatmapGenerator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from layer1_sensor_hub.mmwave.heatmap import HeatmapConfig, HeatmapGenerator


@dataclass
class FakeObject:
    x: float = 0.0
    y: float = 0.0
    range_m: float = 1.5
    snr: float = 15.0
    velocity_mps: float = 0.5
    confidence: float = 0.8
    track_id: str | None = "t1"


@dataclass
class FakeFrame:
    frame_id: int = 1
    objects: list = field(default_factory=list)


def test_heatmap_occupancy_empty() -> None:
    gen = HeatmapGenerator()
    frame = FakeFrame(objects=[])
    h = gen.occupancy(frame)
    assert h.shape == (60, 80)
    assert h.sum() == 0.0


def test_heatmap_occupancy_single_point() -> None:
    gen = HeatmapGenerator()
    frame = FakeFrame(objects=[FakeObject(x=0.0, y=2.0)])
    h = gen.occupancy(frame)
    assert h.shape == (60, 80)
    assert h.sum() == 1.0
    # y=2.0 in height_m=6.0 -> bin_y = 20
    assert h[20, 40] == 1.0


def test_heatmap_occupancy_multiple_points() -> None:
    gen = HeatmapGenerator()
    objects = [
        FakeObject(x=-2.0, y=1.0),
        FakeObject(x=2.0, y=3.0),
        FakeObject(x=2.0, y=3.0),  # same bin -> still 1 (binary)
    ]
    frame = FakeFrame(objects=objects)
    h = gen.occupancy(frame)
    assert h.sum() == 2.0  # two unique bins


def test_heatmap_snr_weighted() -> None:
    gen = HeatmapGenerator()
    frame = FakeFrame(objects=[FakeObject(x=0.0, y=2.0, snr=20.0)])
    h = gen.snr_weighted(frame)
    assert h[20, 40] == 20.0


def test_heatmap_velocity_magnitude() -> None:
    gen = HeatmapGenerator()
    frame = FakeFrame(objects=[FakeObject(x=0.0, y=2.0, velocity_mps=-0.8)])
    h = gen.velocity_magnitude(frame)
    assert np.isclose(h[20, 40], 0.8)  # abs value


def test_heatmap_cumulative_occupancy() -> None:
    gen = HeatmapGenerator()
    f1 = FakeFrame(objects=[FakeObject(x=0.0, y=1.0)])
    f2 = FakeFrame(objects=[FakeObject(x=0.0, y=3.0)])
    h = gen.cumulative_occupancy([f1, f2])
    assert h.sum() == 2.0


def test_heatmap_render(tmp_path: Path) -> None:
    gen = HeatmapGenerator()
    h = np.zeros((60, 80), dtype=np.float32)
    h[30, 40] = 1.0
    out = tmp_path / "test_heatmap.png"
    result = gen.render(h, out)
    assert result.is_file()
    assert result.stat().st_size > 0


def test_heatmap_smoothing() -> None:
    cfg = HeatmapConfig(smoothing_sigma=1.0)
    gen = HeatmapGenerator(cfg)
    frame = FakeFrame(objects=[FakeObject(x=0.0, y=2.0)])
    h = gen.occupancy(frame)
    # smoothed peak should be lower than 1 and spread
    assert h[20, 40] < 1.0
