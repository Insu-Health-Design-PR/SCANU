"""Unit tests for Layer 2 signal processor input contracts."""

from __future__ import annotations

import struct
import unittest
from dataclasses import dataclass, field

import numpy as np

try:
    from software.layer2_signal_processing.test_support import (
        build_layer1_raw_frame,
        ensure_serial_stub,
    )
except ModuleNotFoundError:
    from test_support import build_layer1_raw_frame, ensure_serial_stub


ensure_serial_stub()

from software.layer1_radar.radar_constants import FRAME_HEADER_SIZE, MAGIC_WORD, TLVType
from software.layer2_signal_processing import SignalProcessor


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
    def test_process_parsed_frame_inputs(self) -> None:
        cases = [
            (
                "range profile and points",
                SignalProcessor(doppler_bins=4, time_fn=lambda: 321.0),
                ParsedFrameStub(
                    frame_number=7,
                    timestamp_cycles=123456,
                    range_profile=np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32),
                    points=[
                        ParsedPoint(1.0, 2.0, 3.0, -0.5, 11.0, 4.0),
                        ParsedPoint(-1.0, 0.5, 0.0, 0.25, 7.0, 2.0),
                    ],
                ),
                {
                    "frame_number": 7,
                    "timestamp_ms": 321000.0,
                    "source_timestamp_cycles": 123456,
                    "point_cloud_shape": (2, 6),
                    "range_doppler_bins": 4,
                    "first_x": 1.0,
                    "first_doppler": -0.5,
                },
            ),
            (
                "only points",
                SignalProcessor(doppler_bins=4, time_fn=lambda: 1.5),
                ParsedFrameStub(
                    frame_number=3,
                    timestamp_cycles=50,
                    points=[ParsedPoint(0.1, 0.2, 0.3, 0.4)],
                ),
                {
                    "frame_number": 3,
                    "timestamp_ms": 1500.0,
                    "source_timestamp_cycles": 50,
                    "point_cloud_shape": (1, 6),
                    "range_doppler_bins": 4,
                    "first_x": 0.1,
                    "first_doppler": 0.4,
                },
            ),
        ]

        for label, processor, parsed, expected in cases:
            with self.subTest(label=label):
                processed = processor.process(parsed)

                self.assertEqual(processed.frame_number, expected["frame_number"])
                self.assertEqual(processed.timestamp_ms, expected["timestamp_ms"])
                self.assertEqual(
                    processed.source_timestamp_cycles,
                    expected["source_timestamp_cycles"],
                )
                self.assertEqual(processed.point_cloud.shape, expected["point_cloud_shape"])
                self.assertEqual(processed.range_doppler.shape[1], expected["range_doppler_bins"])
                self.assertAlmostEqual(processed.point_cloud[0, 0], expected["first_x"])
                self.assertAlmostEqual(
                    processed.point_cloud[0, 3],
                    expected["first_doppler"],
                )

    def test_process_json_frame_dict_inputs(self) -> None:
        cases = [
            (
                "range profile and points",
                SignalProcessor(doppler_bins=4, time_fn=lambda: 999.0),
                {
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
                },
                {
                    "frame_number": 12,
                    "timestamp_ms": 999000.0,
                    "source_timestamp_cycles": 424242,
                    "point_cloud_shape": (2, 6),
                    "range_doppler_bins": 4,
                    "first_x": 0.5,
                    "first_doppler": 0.0,
                },
            ),
            (
                "only points",
                SignalProcessor(doppler_bins=4, time_fn=lambda: 2.0),
                {
                    "frame_number": 8,
                    "timestamp": 8080,
                    "points": [
                        {"x": 0.1, "y": 0.2, "z": 0.3, "doppler": 0.4},
                    ],
                },
                {
                    "frame_number": 8,
                    "timestamp_ms": 2000.0,
                    "source_timestamp_cycles": 8080,
                    "point_cloud_shape": (1, 4),
                    "range_doppler_bins": 4,
                    "first_x": 0.1,
                    "first_doppler": 0.4,
                },
            ),
        ]

        for label, processor, frame_dict, expected in cases:
            with self.subTest(label=label):
                processed = processor.process(frame_dict)

                self.assertEqual(processed.frame_number, expected["frame_number"])
                self.assertEqual(processed.timestamp_ms, expected["timestamp_ms"])
                self.assertEqual(
                    processed.source_timestamp_cycles,
                    expected["source_timestamp_cycles"],
                )
                self.assertEqual(processed.point_cloud.shape, expected["point_cloud_shape"])
                self.assertEqual(processed.range_doppler.shape[1], expected["range_doppler_bins"])
                self.assertAlmostEqual(processed.point_cloud[0, 0], expected["first_x"])
                self.assertAlmostEqual(
                    processed.point_cloud[0, 3],
                    expected["first_doppler"],
                )

    def test_process_layer1_raw_bytes_inputs(self) -> None:
        cases = [
            (
                "range profile only",
                SignalProcessor(doppler_bins=16),
                build_layer1_raw_frame(
                    frame_header_size=FRAME_HEADER_SIZE,
                    magic_word=MAGIC_WORD,
                    frame_number=1,
                    timestamp_cycles=111,
                    tlvs=[(TLVType.RANGE_PROFILE, struct.pack("<4H", 10, 20, 30, 40))],
                ),
                {
                    "frame_number": 1,
                    "timestamp_ms": None,
                    "source_timestamp_cycles": 111,
                    "point_cloud_shape": None,
                    "range_doppler_bins": None,
                },
            ),
            (
                "range profile and points",
                SignalProcessor(doppler_bins=4, time_fn=lambda: 9.0),
                build_layer1_raw_frame(
                    frame_header_size=FRAME_HEADER_SIZE,
                    magic_word=MAGIC_WORD,
                    frame_number=11,
                    timestamp_cycles=654321,
                    tlvs=[
                        (TLVType.RANGE_PROFILE, struct.pack("<4H", 10, 20, 30, 40)),
                        (TLVType.DETECTED_POINTS, struct.pack("<4f", 1.0, 2.0, 3.0, -0.5)),
                    ],
                ),
                {
                    "frame_number": 11,
                    "timestamp_ms": 9000.0,
                    "source_timestamp_cycles": 654321,
                    "point_cloud_shape": (1, 6),
                    "range_doppler_bins": 4,
                    "first_x": 1.0,
                    "first_doppler": -0.5,
                },
            ),
        ]

        for label, processor, raw_frame, expected in cases:
            with self.subTest(label=label):
                processed = processor.process(raw_frame)

                self.assertEqual(processed.frame_number, expected["frame_number"])
                self.assertEqual(
                    processed.source_timestamp_cycles,
                    expected["source_timestamp_cycles"],
                )
                if expected["timestamp_ms"] is not None:
                    self.assertEqual(processed.timestamp_ms, expected["timestamp_ms"])
                self.assertEqual(processed.range_doppler.ndim, 2)
                if expected["range_doppler_bins"] is not None:
                    self.assertEqual(
                        processed.range_doppler.shape[1],
                        expected["range_doppler_bins"],
                    )
                if expected["point_cloud_shape"] is not None:
                    self.assertEqual(processed.point_cloud.shape, expected["point_cloud_shape"])
                    self.assertAlmostEqual(processed.point_cloud[0, 0], expected["first_x"])
                    self.assertAlmostEqual(
                        processed.point_cloud[0, 3],
                        expected["first_doppler"],
                    )


if __name__ == "__main__":
    unittest.main()
