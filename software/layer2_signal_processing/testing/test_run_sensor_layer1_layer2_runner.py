"""Tests for the Layer 1 -> Layer 2 live runner example."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

try:
    from software.layer2_signal_processing.testing.test_support import ensure_serial_stub
except ModuleNotFoundError:
    from test_support import ensure_serial_stub


def _load_runner_module():
    ensure_serial_stub()

    module_path = Path(__file__).resolve().parent / "run_sensor_layer1_layer2.py"
    spec = importlib.util.spec_from_file_location("run_sensor_layer1_layer2_runner", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeArray:
    def __init__(self, values, shape) -> None:
        self._values = values
        self.shape = shape

    def tolist(self):
        return self._values


class _FakeProcessed:
    def __init__(self) -> None:
        self.frame_number = 7
        self.timestamp_ms = 123.0
        self.source_timestamp_cycles = 456
        self.range_doppler = _FakeArray([[1.0, 2.0]], (1, 2))
        self.point_cloud = _FakeArray([[3.0, 4.0, 5.0, 6.0, 7.0, 8.0]], (1, 6))


class _FakeFeatures:
    def __init__(self) -> None:
        self.frame_number = 7
        self.timestamp_ms = 123.0
        self.range_heatmap = _FakeArray([1.0, 2.0], (2,))
        self.doppler_heatmap = _FakeArray([3.0, 4.0], (2,))
        self.vector = _FakeArray([5.0, 6.0, 7.0], (3,))


class _FakePacket:
    def __init__(self) -> None:
        self.processed = _FakeProcessed()
        self.features = _FakeFeatures()


class _FakePipeline:
    def __init__(self) -> None:
        self.connected = False
        self.closed = False
        self.connect_kwargs = None

    def connect_and_configure(self, **kwargs) -> None:
        self.connected = True
        self.connect_kwargs = kwargs

    def stream(self, max_frames: int = 0):
        for _ in range(max_frames):
            yield _FakePacket()

    def close(self) -> None:
        self.closed = True


class TestRunSensorLayer1Layer2Runner(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_runner_module()

    def test_validate_args_requires_both_manual_ports(self) -> None:
        parser = self.runner.build_parser()
        args = parser.parse_args(["--cli-port", "/dev/ttyUSB0"])

        with self.assertRaises(SystemExit):
            self.runner._validate_args(parser, args)

    def test_validate_args_requires_existing_config_file(self) -> None:
        parser = self.runner.build_parser()
        args = parser.parse_args(["--config", "/tmp/this_file_should_not_exist.cfg"])

        with self.assertRaises(SystemExit):
            self.runner._validate_args(parser, args)

    def test_check_mode_prints_plan_without_creating_pipeline(self) -> None:
        stdout = io.StringIO()

        def _unexpected_pipeline_factory():
            raise AssertionError("pipeline_factory should not be called in check mode")

        with contextlib.redirect_stdout(stdout):
            exit_code = self.runner.main(["--check", "--frames", "3"], pipeline_factory=_unexpected_pipeline_factory)

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("LIVE SENSOR -> LAYER 1 -> LAYER 2", output)
        self.assertIn("Runtime plan", output)
        self.assertIn("port mode: autodetect", output)
        self.assertIn("Check mode enabled: validation complete, sensor was not started.", output)

    def test_main_runs_pipeline_and_supports_cli_port_alias(self) -> None:
        stdout = io.StringIO()
        pipeline = _FakePipeline()

        def _pipeline_factory():
            return pipeline

        with tempfile.NamedTemporaryFile(suffix=".cfg") as config_file:
            with contextlib.redirect_stdout(stdout):
                exit_code = self.runner.main(
                    [
                        "--cli-port",
                        "/dev/ttyUSB0",
                        "--data-port",
                        "/dev/ttyUSB1",
                        "--config",
                        config_file.name,
                        "--frames",
                        "1",
                        "--full",
                    ],
                    pipeline_factory=_pipeline_factory,
                )

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertTrue(pipeline.connected)
        self.assertTrue(pipeline.closed)
        self.assertEqual(pipeline.connect_kwargs["config_port"], "/dev/ttyUSB0")
        self.assertEqual(pipeline.connect_kwargs["data_port"], "/dev/ttyUSB1")
        self.assertEqual(pipeline.connect_kwargs["config_path"], config_file.name)
        self.assertIn("output mode: full JSON", output)
        self.assertIn('"ProcessedFrame"', output)


if __name__ == "__main__":
    unittest.main()
