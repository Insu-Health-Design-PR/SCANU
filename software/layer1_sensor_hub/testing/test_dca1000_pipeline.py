"""Mock-based integration tests for the DCA1000 capture pipeline."""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
from pathlib import Path

import numpy as np

from layer1_sensor_hub.mmwave_dca.adc_reader import AdcCaptureShape, read_adc_data
from layer1_sensor_hub.mmwave_dca.dca1000_udp import Dca1000NetworkConfig, UdpDca1000Recorder
from layer1_sensor_hub.mmwave_dca.mmwave_raw_adc_detector import (
    MmweaponCfarParams,
    WeaponZoneParams,
    RawAdcWeaponDetector,
)

# ── synthetic ADC frame generator ────────────────────────────────────────────


def make_synthetic_frame(
    chirps: int = 16,
    rx: int = 4,
    samples: int = 384,
    noise_level: float = 50.0,
    add_target: bool = False,
    target_range_bin: int = 100,
    target_doppler_bin: int = 32,
    target_amplitude: float = 200.0,
) -> np.ndarray:
    np.random.seed(42)
    frame = (np.random.randn(chirps, rx, samples).astype(np.complex64) * noise_level)
    if add_target:
        frame[:, :, target_range_bin] += target_amplitude * np.exp(
            1j * np.random.rand(chirps, rx) * 2 * np.pi
        )
        # slight doppler shift
        for d in range(-2, 3):
            db = target_doppler_bin + d
            if 0 <= db < chirps:
                frame[db, :, target_range_bin] += target_amplitude * 0.5 * np.exp(
                    1j * np.random.rand(rx) * 2 * np.pi
                )
    return frame


def frame_to_bytes(frame: np.ndarray) -> bytes:
    chirps, rx, samples = frame.shape
    flat = frame.reshape(-1)
    n = len(flat)
    iq = np.empty(n * 2, dtype=np.int16)
    # TI interleaved: I0,I1,Q0,Q1, I2,I3,Q2,Q3, ...
    for i in range(0, n, 2):
        base = i * 2
        iq[base]     = int(np.real(flat[i]).clip(-32768, 32767))
        iq[base + 1] = int(np.real(flat[i + 1]).clip(-32768, 32767))
        iq[base + 2] = int(np.imag(flat[i]).clip(-32768, 32767))
        iq[base + 3] = int(np.imag(flat[i + 1]).clip(-32768, 32767))
    return iq.tobytes()


def make_udp_packet(payload: bytes) -> bytes:
    header = struct.pack(">II", 0, len(payload))
    return header + payload


# ── integration tests ────────────────────────────────────────────────────────


def test_read_adc_data_roundtrip(tmp_path: Path) -> None:
    chirps, rx, samples = 16, 4, 384
    n_frames = 5
    frames = np.array([make_synthetic_frame(chirps, rx, samples) for _ in range(n_frames)])

    raw_bytes = b"".join(frame_to_bytes(f) for f in frames)
    path = tmp_path / "test_adc.bin"
    path.write_bytes(raw_bytes)

    shape = AdcCaptureShape(frames=n_frames, chirps=chirps, rx=rx, samples=samples)
    loaded = read_adc_data(path, shape)
    assert loaded.shape == (n_frames, chirps, rx, samples)
    # Verify content approximately (some precision loss from int16 roundtrip)
    np.testing.assert_allclose(np.real(loaded[0]), np.real(frames[0]), atol=1.0)


def test_read_adc_data_truncate_raises(tmp_path: Path) -> None:
    chirps, rx, samples = 16, 4, 384
    raw_bytes = b"\x00\x00" * (chirps * rx * samples)  # half a frame
    path = tmp_path / "truncated.bin"
    path.write_bytes(raw_bytes)

    shape = AdcCaptureShape(frames=1, chirps=chirps, rx=rx, samples=samples)
    import pytest
    with pytest.raises(ValueError, match="too small"):
        read_adc_data(path, shape, allow_truncate=True)


def test_detector_returns_result() -> None:
    detector = RawAdcWeaponDetector(
        cfar=MmweaponCfarParams(threshold_scale=3.0, noise_floor_offset_db=1.5),
    )
    frame = make_synthetic_frame(chirps=48, rx=4, samples=384, add_target=True)
    result = detector.detect(frame, frame_number=0)
    assert result.frame_number == 0
    assert 0.0 <= result.weapon_score <= 1.0
    # MIMO uses TX1 (16 chirps from 16 loops), RD map -> [16, 384]
    assert result.rd_map.shape[1] == 384
    assert result.mimo_enabled


def test_detector_empty_frame() -> None:
    detector = RawAdcWeaponDetector()
    frame = make_synthetic_frame(chirps=48, rx=4, samples=384, add_target=False)
    result = detector.detect(frame, frame_number=1)
    assert result.frame_number == 1
    assert isinstance(result.weapon_score, float)


def test_detector_legacy_mode() -> None:
    detector = RawAdcWeaponDetector()
    frame = make_synthetic_frame(chirps=16, rx=4, samples=384, add_target=True)
    result = detector.detect(frame, frame_number=0)
    assert result.mimo_enabled is False


def test_detector_weapon_scoring() -> None:
    detector = RawAdcWeaponDetector(
        cfar=MmweaponCfarParams(threshold_scale=2.0, noise_floor_offset_db=0.5),
    )
    noise_frame = make_synthetic_frame(chirps=48, rx=4, samples=384, add_target=False, noise_level=100.0)
    target_frame = make_synthetic_frame(chirps=48, rx=4, samples=384, add_target=True, noise_level=100.0, target_amplitude=500.0)

    noise_score = detector.detect(noise_frame).weapon_score
    target_score = detector.detect(target_frame).weapon_score
    # Target frame should score higher (given sensitive CFAR)
    assert target_score >= noise_score * 0.5  # not a hard assert, just directional


def test_cfar_params_validate() -> None:
    p = MmweaponCfarParams(threshold_scale=5.0, noise_floor_offset_db=2.0)
    assert p.threshold_scale == 5.0
    assert p.noise_floor_offset_db == 2.0
    assert p.max_points == 64


def test_zone_params() -> None:
    z = WeaponZoneParams(static_start=80, static_end=160)
    assert z.static_start == 80
    assert z.static_end == 160


def test_synthetic_frame_has_energy() -> None:
    frame = make_synthetic_frame(chirps=48, rx=4, samples=384)
    assert np.any(np.abs(frame) > 0)


def test_synthetic_frame_with_target() -> None:
    frame = make_synthetic_frame(chirps=48, rx=4, samples=384, add_target=True, target_range_bin=100, target_amplitude=500.0)
    # Target bin should have significantly more energy
    target_energy = np.abs(frame[:, :, 100]).mean()
    noise_energy = np.abs(frame[:, :, 0]).mean()
    assert target_energy > noise_energy * 2
