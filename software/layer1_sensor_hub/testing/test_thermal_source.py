"""Tests for ThermalCameraSource helpers."""

from __future__ import annotations

import numpy as np

from layer1_sensor_hub.thermal.thermal_source import (
    normalize_thermal_frame,
    _is_numeric_device,
)


def test_normalize_uint16() -> None:
    frame = np.zeros((10, 20), dtype=np.uint16)
    frame[5, 10] = 65535
    norm = normalize_thermal_frame(frame)
    assert norm.dtype == np.uint8
    assert norm.max() == 255
    assert norm.min() == 0
    assert norm[5, 10] == 255


def test_normalize_uint16_uniform() -> None:
    frame = np.full((10, 20), 1000, dtype=np.uint16)
    norm = normalize_thermal_frame(frame)
    assert norm.sum() == 0.0


def test_normalize_uint8() -> None:
    frame = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
    norm = normalize_thermal_frame(frame)
    assert norm.dtype == np.uint8
    assert norm.shape == frame.shape


def test_normalize_bgr() -> None:
    frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    norm = normalize_thermal_frame(frame)
    assert norm.ndim == 2
    assert norm.shape == (100, 100)


def test_normalize_float() -> None:
    frame = np.random.rand(100, 100).astype(np.float32) * 255.0
    norm = normalize_thermal_frame(frame)
    assert norm.dtype == np.uint8


def test_is_numeric_device() -> None:
    assert _is_numeric_device(0) is True
    assert _is_numeric_device("0") is True
    assert _is_numeric_device("/dev/video0") is False
    assert _is_numeric_device("/dev/v4l/by-id/test") is False
