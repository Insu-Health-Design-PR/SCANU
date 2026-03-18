"""Unit tests for common port scanner."""

from __future__ import annotations

from dataclasses import dataclass
import unittest

from software.layer1_sensors_unified.common import PortScanner


@dataclass
class _FakePort:
    device: str
    description: str
    manufacturer: str = ""
    vid: int | None = None
    pid: int | None = None
    hwid: str = ""


class TestPortScanner(unittest.TestCase):
    def test_scan_from_records(self) -> None:
        records = [
            _FakePort("/dev/ttyUSB0", "USB Serial", "Silicon Labs", 0x10C4, 0xEA60, "A"),
            _FakePort("/dev/ttyACM0", "XDS110", "Texas Instruments", 0x0451, 0xBEF3, "B"),
        ]

        ports = PortScanner.scan(records)

        self.assertEqual(len(ports), 2)
        self.assertEqual(ports[0].device, "/dev/ttyUSB0")
        self.assertEqual(ports[1].vid, 0x0451)


if __name__ == "__main__":
    unittest.main()
