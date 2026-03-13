"""Compatibility tests for ESP32 firmware JSON output format."""

from __future__ import annotations

import unittest

from software.layer1_aux_sensors import AuxProtocol


class TestFirmwareOutputCompatibility(unittest.TestCase):
    def test_firmware_reading_line_is_parseable(self) -> None:
        protocol = AuxProtocol()
        line = (
            '{"type":"reading","frame_id":12,"ts_device_ms":9876,"readings":['
            '{"sensor_id":"pir_1","sensor_type":"pir","value":1,"unit":"bool","quality":1.0},'
            '{"sensor_id":"rf_1","sensor_type":"rf","value":0,"unit":"bool","quality":1.0},'
            '{"sensor_id":"thermal_probe_1","sensor_type":"thermal_probe","value":27.125,"unit":"celsius","quality":1.0}'
            ']}'
        )

        parsed = protocol.decode_line(line)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.kind, "frame")
        frame = parsed.payload
        self.assertEqual(frame.frame_id, 12)
        self.assertEqual(len(frame.readings), 3)
        self.assertEqual(frame.readings[2].sensor_type, "thermal_probe")

    def test_firmware_heartbeat_line_is_parseable(self) -> None:
        protocol = AuxProtocol()
        line = '{"type":"heartbeat","device_id":"esp32_aux_01","fw":"0.1.0","uptime_ms":54321}'

        parsed = protocol.decode_line(line)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.kind, "heartbeat")
        self.assertEqual(parsed.payload.device_id, "esp32_aux_01")


if __name__ == "__main__":
    unittest.main()
