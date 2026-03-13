"""Unit tests for ESP32 auxiliary sensor port resolver."""

from __future__ import annotations

import unittest

from software.layer1_sensors_unified.aux_sensors.port_resolver import AuxSensorPortResolver
from software.layer1_sensors_unified.common import PortInfo


class TestAuxSensorPortResolver(unittest.TestCase):
    def test_find_candidates(self) -> None:
        ports = (
            PortInfo("/dev/ttyACM0", "XDS110", "Texas Instruments", 0x0451, 0xBEF3, ""),
            PortInfo("/dev/ttyUSB0", "CP210x USB to UART", "Silicon Labs", 0x10C4, 0xEA60, ""),
        )

        matches = AuxSensorPortResolver.find_candidates(ports)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].device, "/dev/ttyUSB0")


if __name__ == "__main__":
    unittest.main()
