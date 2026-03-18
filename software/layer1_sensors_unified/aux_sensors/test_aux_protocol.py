"""Unit tests for auxiliary JSON line protocol parsing."""

from __future__ import annotations

import unittest

from software.layer1_sensors_unified.aux_sensors import AuxProtocol


class TestAuxProtocol(unittest.TestCase):
    def test_decode_reading(self) -> None:
        protocol = AuxProtocol()
        line = (
            '{"type":"reading","frame_id":9,"ts_device_ms":123.0,'
            '"readings":[{"sensor_id":"pir_1","sensor_type":"pir","value":1,"unit":"bool","quality":0.9}]}'
        )

        parsed = protocol.decode_line(line)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.kind, "frame")
        frame = parsed.payload
        self.assertEqual(frame.frame_id, 9)
        self.assertEqual(len(frame.readings), 1)
        self.assertEqual(frame.readings[0].sensor_id, "pir_1")

    def test_decode_heartbeat(self) -> None:
        protocol = AuxProtocol()
        parsed = protocol.decode_line(
            '{"type":"heartbeat","device_id":"esp32_aux_01","fw":"0.1.0","uptime_ms":4567}'
        )

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.kind, "heartbeat")
        heartbeat = parsed.payload
        self.assertEqual(heartbeat.device_id, "esp32_aux_01")
        self.assertEqual(heartbeat.uptime_ms, 4567)

    def test_encode_command(self) -> None:
        protocol = AuxProtocol()
        encoded = protocol.encode_command({"b": 2, "a": 1})
        self.assertEqual(encoded, '{"a":1,"b":2}')


if __name__ == "__main__":
    unittest.main()
