"""Unit tests for PresenceSource and MockPresenceProvider."""

from __future__ import annotations

import unittest

from software.layer1_sensors_unified.radar_presence_60g import (
    BGT60LTR11AIP_SENSOR_MODEL,
    BGT60LTR11AIPSerialProvider,
    DEMOBGT60LTR11AIPTOBO1_BOARD_KIT,
    MockPresenceProvider,
    PresenceSample,
    PresenceSource,
)


class TestPresenceSource(unittest.TestCase):
    def test_source_sequence(self) -> None:
        source = PresenceSource(MockPresenceProvider())

        f1 = source.read_frame()
        f2 = source.read_frame()
        f3 = source.read_frame()

        self.assertEqual(f1.frame_number, 1)
        self.assertEqual(f2.frame_number, 2)
        self.assertEqual(f3.frame_number, 3)
        self.assertGreaterEqual(f1.distance_m, 0.0)
        self.assertEqual(f1.sensor_model, BGT60LTR11AIP_SENSOR_MODEL)
        self.assertEqual(f1.board_kit, DEMOBGT60LTR11AIPTOBO1_BOARD_KIT)
        self.assertGreater(f1.signal_quality, 0.0)

    def test_source_accepts_structured_sample(self) -> None:
        class StaticProvider:
            def read_sample(self) -> PresenceSample:
                return PresenceSample(
                    presence_raw=0.7,
                    motion_raw=0.2,
                    distance_m=1.5,
                    signal_quality=0.65,
                    temperature_c=31.2,
                )

        frame = PresenceSource(StaticProvider()).read_frame()

        self.assertAlmostEqual(frame.presence_raw, 0.7)
        self.assertAlmostEqual(frame.signal_quality, 0.65)
        self.assertAlmostEqual(frame.temperature_c or 0.0, 31.2)


class TestBGT60LTR11AIPSerialProvider(unittest.TestCase):
    def test_parse_json_line(self) -> None:
        provider = BGT60LTR11AIPSerialProvider()

        sample = provider.parse_line(
            '{"presence": 1, "motion": 0.4, "distance_m": 1.8, "quality": 0.9, "temperature_c": 30.5}'
        )

        self.assertIsNotNone(sample)
        assert sample is not None
        self.assertAlmostEqual(sample.presence_raw, 1.0)
        self.assertAlmostEqual(sample.motion_raw, 0.4)
        self.assertAlmostEqual(sample.distance_m, 1.8)
        self.assertAlmostEqual(sample.signal_quality, 0.9)
        self.assertAlmostEqual(sample.temperature_c or 0.0, 30.5)

    def test_parse_key_value_line(self) -> None:
        provider = BGT60LTR11AIPSerialProvider()

        sample = provider.parse_line("presence=0.7 motion=0.2 distance=2.3 quality=0.88")

        self.assertIsNotNone(sample)
        assert sample is not None
        self.assertAlmostEqual(sample.presence_raw, 0.7)
        self.assertAlmostEqual(sample.motion_raw, 0.2)
        self.assertAlmostEqual(sample.distance_m, 2.3)
        self.assertAlmostEqual(sample.signal_quality, 0.88)

    def test_parse_status_line(self) -> None:
        provider = BGT60LTR11AIPSerialProvider()

        sample = provider.parse_line("Presence detected, direction=approaching")

        self.assertIsNotNone(sample)
        assert sample is not None
        self.assertAlmostEqual(sample.presence_raw, 1.0)
        self.assertGreater(sample.motion_raw, 0.0)
        self.assertAlmostEqual(sample.distance_m, -1.0)

    def test_read_sample_skips_noise_lines(self) -> None:
        class FakeSerial:
            def __init__(self) -> None:
                self.is_open = True
                self._lines = iter(
                    [
                        b"\n",
                        b"PSoC 6 MCU: BGT60LTR11 RADAR example\n",
                        b"presence=1 motion=0.6 distance=1.1 quality=0.95\n",
                    ]
                )

            def readline(self, _max_line_bytes: int) -> bytes:
                return next(self._lines, b"")

        provider = BGT60LTR11AIPSerialProvider(serial_port=FakeSerial())
        sample = provider.read_sample()

        self.assertAlmostEqual(sample.presence_raw, 1.0)
        self.assertAlmostEqual(sample.motion_raw, 0.6)
        self.assertAlmostEqual(sample.distance_m, 1.1)
        self.assertAlmostEqual(sample.signal_quality, 0.95)


if __name__ == "__main__":
    unittest.main()
