"""Unit tests for AuxSensorSource reconnection and metrics."""

from __future__ import annotations

from dataclasses import dataclass
import unittest

from software.layer1_sensors_unified.aux_sensors import AuxHealthConfig, AuxSensorSource


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


@dataclass
class _Cfg:
    reconnect_backoff_s: float = 0.0


class FakeBridge:
    def __init__(
        self,
        lines: list[bytes],
        *,
        connected: bool = True,
        connect_failures: int = 0,
        read_failures: int = 0,
    ) -> None:
        self.config = _Cfg()
        self._lines = lines
        self._connected = connected
        self._connect_failures = connect_failures
        self._read_failures = read_failures

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        if self._connect_failures > 0:
            self._connect_failures -= 1
            raise RuntimeError("connect failed")
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def readline(self) -> bytes:
        if not self._connected:
            raise RuntimeError("disconnected")
        if self._read_failures > 0:
            self._read_failures -= 1
            self._connected = False
            raise RuntimeError("read failed")
        if not self._lines:
            return b""
        return self._lines.pop(0)


class TestAuxSource(unittest.TestCase):
    def test_parsing_and_metrics(self) -> None:
        lines = [
            b'{"type":"heartbeat","device_id":"esp32_aux_01","fw":"0.1.0","uptime_ms":10}\n',
            b'{"type":"reading","frame_id":1,"ts_device_ms":20,"readings":[{"sensor_id":"pir_1","sensor_type":"pir","value":1,"unit":"bool","quality":1.0}]}\n',
            b'not-json\n',
            b'\n',
            b'{"type":"unknown"}\n',
        ]
        clock = FakeClock()
        bridge = FakeBridge(lines)
        source = AuxSensorSource(bridge=bridge, time_fn=clock.time, sleep_fn=clock.sleep)

        frame = None
        for _ in range(5):
            maybe = source.read_once()
            if maybe is not None:
                frame = maybe

        self.assertIsNotNone(frame)
        stats = source.get_stats()
        self.assertEqual(stats["frames"], 1)
        self.assertEqual(stats["heartbeats"], 1)
        self.assertEqual(stats["parse_errors"], 1)
        self.assertEqual(stats["invalid_messages"], 2)
        self.assertEqual(stats["empty_lines"], 1)
        self.assertEqual(stats["dropped_messages"], 2)

    def test_auto_reconnect_when_disconnected(self) -> None:
        lines = [
            b'{"type":"reading","frame_id":2,"ts_device_ms":33,"readings":[]}\n',
        ]
        clock = FakeClock()
        bridge = FakeBridge(lines, connected=False)
        source = AuxSensorSource(bridge=bridge, time_fn=clock.time, sleep_fn=clock.sleep)

        frame = source.read_once()

        self.assertIsNotNone(frame)
        stats = source.get_stats()
        self.assertEqual(stats["reconnect_attempts"], 1)
        self.assertEqual(stats["reconnect_count"], 1)

    def test_read_failure_triggers_reconnect(self) -> None:
        lines = [
            b'{"type":"reading","frame_id":3,"ts_device_ms":44,"readings":[]}\n',
        ]
        clock = FakeClock()
        bridge = FakeBridge(lines, connected=True, read_failures=1)
        source = AuxSensorSource(bridge=bridge, time_fn=clock.time, sleep_fn=clock.sleep)

        first = source.read_once()
        second = source.read_once()

        self.assertIsNone(first)
        self.assertIsNotNone(second)
        stats = source.get_stats()
        self.assertEqual(stats["read_errors"], 1)
        self.assertGreaterEqual(int(stats["reconnect_count"]), 1)

    def test_heartbeat_loss_count(self) -> None:
        lines = [
            b'{"type":"heartbeat","device_id":"esp32_aux_01","fw":"0.1.0","uptime_ms":10}\n',
            b'\n',
        ]
        clock = FakeClock()
        bridge = FakeBridge(lines)
        source = AuxSensorSource(
            bridge=bridge,
            health_config=AuxHealthConfig(heartbeat_timeout_s=1.0, stream_timeout_s=5.0),
            time_fn=clock.time,
            sleep_fn=clock.sleep,
        )

        source.read_once()  # heartbeat
        clock.sleep(2.0)
        source.read_once()  # trigger timeout check

        stats = source.get_stats()
        self.assertEqual(stats["heartbeat_loss_count"], 1)


if __name__ == "__main__":
    unittest.main()
