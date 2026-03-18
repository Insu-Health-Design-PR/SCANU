"""Unit tests for Layer 2 signal processor input contracts."""

from __future__ import annotations

import struct
import sys
import types
import unittest
from dataclasses import dataclass, field

import numpy as np

def _ensure_serial_stub() -> None:
    if "serial" in sys.modules:
        return

    serial_module = types.ModuleType("serial")
    serial_module.SerialException = Exception
    serial_module.Serial = object
    serial_module.EIGHTBITS = 8
    serial_module.PARITY_NONE = "N"
    serial_module.STOPBITS_ONE = 1

    serial_tools = types.ModuleType("serial.tools")
    serial_list_ports = types.ModuleType("serial.tools.list_ports")
    serial_list_ports.comports = lambda: []
    serial_tools.list_ports = serial_list_ports
    serial_module.tools = serial_tools

    sys.modules["serial"] = serial_module
    sys.modules["serial.tools"] = serial_tools
    sys.modules["serial.tools.list_ports"] = serial_list_ports


_ensure_serial_stub()

from software.layer2_signal_processing import SignalProcessor
from software.layer1_radar.radar_constants import FRAME_HEADER_SIZE, MAGIC_WORD, TLVType


def _build_layer1_raw_frame(
    frame_number: int,
    timestamp_cycles: int,
    tlvs: list[tuple[int, bytes]],
) -> bytes:
    body = bytearray()
    for tlv_type, data in tlvs:
        body.extend(struct.pack("<II", tlv_type, len(data)))
        body.extend(data)

    total_len = FRAME_HEADER_SIZE + len(body)
    header_fields = struct.pack(
        "<8I",
        0x01020304,
        total_len,
        0x6843,
        frame_number,
        timestamp_cycles,
        0,
        len(tlvs),
        0,
    )
    return MAGIC_WORD + header_fields + bytes(body)


@dataclass
class ParsedPoint:
    x: float
    y: float
    z: float
    doppler: float
    snr: float = 0.0
    noise: float = 0.0


@dataclass
class ParsedFrameStub:
    frame_number: int
    timestamp_cycles: int
    points: list[ParsedPoint] = field(default_factory=list)
    range_profile: np.ndarray | None = None
    noise_profile: np.ndarray | None = None


class TestSignalProcessor(unittest.TestCase):
    def test_process_layer1_raw_bytes_minimal(self) -> None:
        processor = SignalProcessor(doppler_bins=16)
        range_profile = struct.pack("<4H", 10, 20, 30, 40)
        raw_frame = _build_layer1_raw_frame(
            frame_number=1,
            timestamp_cycles=111,
            tlvs=[(TLVType.RANGE_PROFILE, range_profile)],
        )

        processed = processor.process(raw_frame)

        self.assertEqual(processed.frame_number, 1)
        self.assertEqual(processed.source_timestamp_cycles, 111)
        self.assertEqual(processed.range_doppler.ndim, 2)

    def test_process_parsed_frame_prefers_range_profile_and_points(self) -> None:
        processor = SignalProcessor(doppler_bins=4, time_fn=lambda: 321.0)
        parsed = ParsedFrameStub(
            frame_number=7,
            timestamp_cycles=123456,
            range_profile=np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32),
            points=[
                ParsedPoint(1.0, 2.0, 3.0, -0.5, 11.0, 4.0),
                ParsedPoint(-1.0, 0.5, 0.0, 0.25, 7.0, 2.0),
            ],
        )

        processed = processor.process(parsed)

        self.assertEqual(processed.frame_number, 7)
        self.assertEqual(processed.timestamp_ms, 321000.0)
        self.assertEqual(processed.source_timestamp_cycles, 123456)
        self.assertEqual(processed.range_doppler.shape[1], 4)
        self.assertEqual(processed.point_cloud.shape, (2, 6))
        self.assertAlmostEqual(processed.point_cloud[0, 0], 1.0)
        self.assertAlmostEqual(processed.point_cloud[0, 3], -0.5)

    def test_process_parsed_frame_with_only_points(self) -> None:
        processor = SignalProcessor(doppler_bins=4, time_fn=lambda: 1.5)
        parsed = ParsedFrameStub(
            frame_number=3,
            timestamp_cycles=50,
            points=[ParsedPoint(0.1, 0.2, 0.3, 0.4)],
        )

        processed = processor.process(parsed)

        self.assertEqual(processed.point_cloud.shape, (1, 6))
        self.assertEqual(processed.range_doppler.ndim, 2)
        self.assertEqual(processed.timestamp_ms, 1500.0)
        self.assertEqual(processed.source_timestamp_cycles, 50)

    def test_process_json_frame_dict_uses_range_profile_and_timestamp(self) -> None:
        processor = SignalProcessor(doppler_bins=4, time_fn=lambda: 999.0)
        frame_dict = {
            "frame_number": 12,
            "timestamp": 424242,
            "num_points": 2,
            "has_range_profile": True,
            "range_profile": [10.0, 20.0, 30.0, 40.0],
            "points": [
                {
                    "x": 0.5,
                    "y": 1.0,
                    "z": 1.5,
                    "doppler": 0.0,
                    "snr": 12.0,
                    "noise": 3.5,
                },
                {
                    "x": -0.5,
                    "y": 0.25,
                    "z": 0.0,
                    "doppler": -0.25,
                    "snr": 8.0,
                    "noise": 2.0,
                },
            ],
        }

        processed = processor.process(frame_dict)

        self.assertEqual(processed.frame_number, 12)
        self.assertEqual(processed.source_timestamp_cycles, 424242)
        self.assertEqual(processed.timestamp_ms, 999000.0)
        self.assertEqual(processed.range_doppler.shape[1], 4)
        self.assertEqual(processed.point_cloud.shape, (2, 6))
        self.assertAlmostEqual(processed.point_cloud[0, 0], 0.5)
        self.assertAlmostEqual(processed.point_cloud[1, 3], -0.25)

    def test_process_json_frame_dict_with_only_points(self) -> None:
        processor = SignalProcessor(doppler_bins=4, time_fn=lambda: 2.0)
        frame_dict = {
            "frame_number": 8,
            "timestamp": 8080,
            "points": [
                {"x": 0.1, "y": 0.2, "z": 0.3, "doppler": 0.4},
            ],
        }

        processed = processor.process(frame_dict)

        self.assertEqual(processed.frame_number, 8)
        self.assertEqual(processed.source_timestamp_cycles, 8080)
        self.assertEqual(processed.timestamp_ms, 2000.0)
        self.assertEqual(processed.point_cloud.shape, (1, 4))
        self.assertEqual(processed.range_doppler.ndim, 2)

    def test_process_layer1_raw_bytes(self) -> None:
        _ensure_serial_stub()
        processor = SignalProcessor(doppler_bins=4, time_fn=lambda: 9.0)

        range_profile = struct.pack("<4H", 10, 20, 30, 40)
        points_data = struct.pack("<4f", 1.0, 2.0, 3.0, -0.5)
        raw_frame = _build_layer1_raw_frame(
            frame_number=11,
            timestamp_cycles=654321,
            tlvs=[
                (TLVType.RANGE_PROFILE, range_profile),
                (TLVType.DETECTED_POINTS, points_data),
            ],
        )

        processed = processor.process(raw_frame)

        self.assertEqual(processed.frame_number, 11)
        self.assertEqual(processed.timestamp_ms, 9000.0)
        self.assertEqual(processed.source_timestamp_cycles, 654321)
        self.assertEqual(processed.point_cloud.shape, (1, 6))
        self.assertAlmostEqual(processed.point_cloud[0, 0], 1.0)
        self.assertAlmostEqual(processed.point_cloud[0, 3], -0.5)
        self.assertEqual(processed.range_doppler.shape[1], 4)


if __name__ == "__main__":
    unittest.main()
