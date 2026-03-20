"""Tests for the realtime Layer 1 -> Layer 2 bridge."""

from __future__ import annotations

import unittest

import numpy as np

try:
    from software.layer2_signal_processing.testing.test_support import ensure_serial_stub
except ModuleNotFoundError:
    from test_support import ensure_serial_stub


ensure_serial_stub()

from software.layer2_signal_processing.live_pipeline import Layer1RealtimePipeline
from software.layer2_signal_processing.signal_processor import ProcessedFrame
from software.layer2_signal_processing.feature_extractor import HeatmapFeatures


class _FakeSignalProcessor:
    def process(self, frame: bytes) -> ProcessedFrame:
        return ProcessedFrame(
            frame_number=5,
            timestamp_ms=1000.0,
            range_doppler=np.ones((2, 2), dtype=np.float32),
            point_cloud=np.ones((3, 6), dtype=np.float32),
            source_timestamp_cycles=123,
        )


class _FakeFeatureExtractor:
    def extract(self, processed: ProcessedFrame) -> HeatmapFeatures:
        return HeatmapFeatures(
            frame_number=processed.frame_number,
            timestamp_ms=processed.timestamp_ms,
            range_heatmap=np.array([1.0, 2.0], dtype=np.float32),
            doppler_heatmap=np.array([3.0, 4.0], dtype=np.float32),
            vector=np.array([5.0, 6.0, 7.0, 8.0, 3.0], dtype=np.float32),
        )


class _FakeUARTSource:
    def __init__(self, frames: list[bytes]) -> None:
        self.frames = frames

    def stream_frames(self, max_frames: int = 0):
        count = 0
        for frame in self.frames:
            if max_frames and count >= max_frames:
                break
            count += 1
            yield frame

    def clear_buffer(self) -> int:
        return 0


class _FakeConfigurator:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class _FakeSerialManager:
    is_connected = True

    def disconnect(self) -> None:
        self.is_connected = False


class TestLivePipeline(unittest.TestCase):
    def test_stream_yields_processed_and_features(self) -> None:
        pipeline = Layer1RealtimePipeline(
            serial_manager=_FakeSerialManager(),
            signal_processor=_FakeSignalProcessor(),
            feature_extractor=_FakeFeatureExtractor(),
        )
        pipeline.configurator = _FakeConfigurator()
        pipeline.uart_source = _FakeUARTSource([b"a", b"b"])

        packets = list(pipeline.stream(max_frames=2))

        self.assertEqual(len(packets), 2)
        self.assertEqual(packets[0].raw_frame, b"a")
        self.assertEqual(packets[1].processed.frame_number, 5)
        self.assertEqual(packets[0].features.vector.tolist(), [5.0, 6.0, 7.0, 8.0, 3.0])

    def test_close_stops_and_disconnects(self) -> None:
        serial_manager = _FakeSerialManager()
        pipeline = Layer1RealtimePipeline(
            serial_manager=serial_manager,
            signal_processor=_FakeSignalProcessor(),
            feature_extractor=_FakeFeatureExtractor(),
        )
        pipeline.configurator = _FakeConfigurator()

        pipeline.close()

        self.assertTrue(pipeline.configurator.stopped)
        self.assertFalse(serial_manager.is_connected)


if __name__ == "__main__":
    unittest.main()
