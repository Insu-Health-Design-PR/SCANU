"""Unit tests for Layer 1 TLV parser, hosted under Layer 2 tasks."""

from __future__ import annotations

import struct
import unittest

try:
    from software.layer2_signal_processing.test_support import ensure_serial_stub
except ModuleNotFoundError:
    from test_support import ensure_serial_stub


ensure_serial_stub()

from software.layer1_radar.radar_constants import FRAME_HEADER_SIZE, MAGIC_WORD, TLVType
from software.layer1_radar.tlv_parser import TLVParser


def _build_frame(frame_number: int, num_detected_obj: int, tlvs: list[tuple[int, bytes]]) -> bytes:
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
        123456,
        num_detected_obj,
        len(tlvs),
        0,
    )
    return MAGIC_WORD + header_fields + bytes(body)


class TestTLVParser(unittest.TestCase):
    def test_parse_detected_points_and_side_info(self) -> None:
        points_data = struct.pack("<4f4f", 1.0, 2.0, 3.0, -0.5, -1.0, 0.5, 0.0, 0.25)
        side_data = struct.pack("<2h2h", 110, 40, 70, 20)

        frame = _build_frame(
            frame_number=42,
            num_detected_obj=2,
            tlvs=[
                (TLVType.DETECTED_POINTS, points_data),
                (TLVType.DETECTED_POINTS_SIDE_INFO, side_data),
            ],
        )

        parsed = TLVParser().parse(frame)

        self.assertEqual(parsed.frame_number, 42)
        self.assertEqual(len(parsed.points), 2)
        self.assertAlmostEqual(parsed.points[0].x, 1.0)
        self.assertAlmostEqual(parsed.points[1].doppler, 0.25)
        self.assertAlmostEqual(parsed.points[0].snr, 11.0)
        self.assertAlmostEqual(parsed.points[1].noise, 2.0)

    def test_parse_range_profile_and_stats(self) -> None:
        range_profile = struct.pack("<4H", 10, 20, 30, 40)
        stats = struct.pack("<6I", 1, 2, 3, 4, 5, 6)

        frame = _build_frame(
            frame_number=7,
            num_detected_obj=0,
            tlvs=[
                (TLVType.RANGE_PROFILE, range_profile),
                (TLVType.STATS, stats),
            ],
        )

        parsed = TLVParser().parse(frame)

        self.assertIsNotNone(parsed.range_profile)
        self.assertEqual(parsed.range_profile.tolist(), [10.0, 20.0, 30.0, 40.0])
        self.assertEqual(parsed.stats["active_frame_cpu_load"], 5)

    def test_truncated_tlv_does_not_crash(self) -> None:
        # Declared TLV data is 16 bytes but frame only carries 4 bytes.
        body = struct.pack("<II", TLVType.RANGE_PROFILE, 16) + b"\x01\x00\x02\x00"
        total_len = FRAME_HEADER_SIZE + len(body)
        header_fields = struct.pack("<8I", 1, total_len, 0x6843, 1, 0, 0, 1, 0)
        frame = MAGIC_WORD + header_fields + body

        parsed = TLVParser().parse(frame)

        self.assertEqual(parsed.frame_number, 1)
        self.assertEqual(len(parsed.raw_tlvs), 0)


if __name__ == "__main__":
    unittest.main()
