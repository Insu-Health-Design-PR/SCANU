"""Unit tests for PresenceSource and MockPresenceProvider."""

from __future__ import annotations

import unittest

from software.layer1_radar_presence_60g import MockPresenceProvider, PresenceSource


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


if __name__ == "__main__":
    unittest.main()
