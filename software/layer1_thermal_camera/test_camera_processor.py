"""Unit tests for thermal camera feature extraction."""

from __future__ import annotations

import unittest

import numpy as np

from software.layer1_thermal_camera import ThermalFrame, ThermalProcessor


class TestThermalProcessor(unittest.TestCase):
    def test_extract_features(self) -> None:
        processor = ThermalProcessor(hotspot_threshold_c=28.0)
        frame = ThermalFrame(
            frame_number=5,
            timestamp_ms=100.0,
            temperature_c=np.array([[27.0, 29.0], [30.0, 25.0]], dtype=np.float32),
        )

        features = processor.extract(frame)

        self.assertEqual(features.frame_number, 5)
        self.assertAlmostEqual(features.max_temp_c, 30.0)
        self.assertAlmostEqual(features.mean_temp_c, 27.75)
        self.assertAlmostEqual(features.hotspot_ratio, 0.5)
        self.assertAlmostEqual(features.presence_score, 1.0)

    def test_extract_empty_frame(self) -> None:
        processor = ThermalProcessor()
        frame = ThermalFrame(frame_number=1, timestamp_ms=1.0, temperature_c=np.array([], dtype=np.float32))

        features = processor.extract(frame)

        self.assertEqual(features.max_temp_c, 0.0)
        self.assertEqual(features.mean_temp_c, 0.0)
        self.assertEqual(features.hotspot_ratio, 0.0)
        self.assertEqual(features.presence_score, 0.0)


if __name__ == "__main__":
    unittest.main()
