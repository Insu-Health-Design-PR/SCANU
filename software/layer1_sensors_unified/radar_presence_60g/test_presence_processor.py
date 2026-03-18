"""Unit tests for PresenceProcessor."""

from __future__ import annotations

import unittest

from software.layer1_sensors_unified.radar_presence_60g import PresenceFrame, PresenceProcessor


class TestPresenceProcessor(unittest.TestCase):
    def test_extract_presence_true(self) -> None:
        processor = PresenceProcessor(presence_threshold=0.5)
        frame = PresenceFrame(
            frame_number=10,
            timestamp_ms=1000.0,
            presence_raw=0.8,
            motion_raw=0.6,
            distance_m=1.3,
        )

        features = processor.extract(frame)

        self.assertEqual(features.frame_number, 10)
        self.assertTrue(features.is_present)
        self.assertAlmostEqual(features.presence_score, 0.8)
        self.assertAlmostEqual(features.confidence, 0.7)

    def test_extract_clamps_bounds(self) -> None:
        processor = PresenceProcessor(presence_threshold=0.5)
        frame = PresenceFrame(
            frame_number=11,
            timestamp_ms=1000.0,
            presence_raw=1.5,
            motion_raw=-0.5,
            distance_m=2.0,
        )

        features = processor.extract(frame)

        self.assertAlmostEqual(features.presence_score, 1.0)
        self.assertAlmostEqual(features.confidence, 0.5)
        self.assertTrue(features.is_present)


if __name__ == "__main__":
    unittest.main()
