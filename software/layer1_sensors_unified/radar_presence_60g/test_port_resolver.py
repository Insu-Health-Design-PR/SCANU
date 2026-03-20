"""Unit tests for Infineon 60 GHz port resolver."""

from __future__ import annotations

import unittest

from software.layer1_sensors_unified.common import PortInfo
from software.layer1_sensors_unified.radar_presence_60g.port_resolver import Presence60GPortResolver


class TestPresence60GPortResolver(unittest.TestCase):
    def test_find_candidates(self) -> None:
        ports = (
            PortInfo("/dev/ttyUSB0", "CP210x USB to UART", "Silicon Labs", 0x10C4, 0xEA60, ""),
            PortInfo("/dev/ttyACM1", "BGT60 Radar Presence", "Infineon", None, None, ""),
        )

        matches = Presence60GPortResolver.find_candidates(ports)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].device, "/dev/ttyACM1")

    def test_exact_xensiv_match_ranks_first(self) -> None:
        ports = (
            PortInfo("/dev/ttyACM1", "Infineon Radar Presence", "Infineon", None, None, ""),
            PortInfo(
                "/dev/ttyACM0",
                "XENSIV BGT60LTR11AIP DEMOBGT60LTR11AIPTOBO1",
                "Infineon",
                None,
                None,
                "",
            ),
        )

        matches = Presence60GPortResolver.find_candidates(ports)

        self.assertEqual(matches[0].device, "/dev/ttyACM0")


if __name__ == "__main__":
    unittest.main()
