"""Public API for Layer 2 signal processing."""

from .calibration import BackgroundModel
from .frame_buffer import FrameBuffer, RadarFrame
from .mockdata import MockFrameSpec, build_mock_processed_frame, build_mock_radar_frame, build_mock_sequence
from .signal_processor import ProcessedFrame, SignalProcessor

__all__ = [
    "BackgroundModel",
    "FrameBuffer",
    "MockFrameSpec",
    "ProcessedFrame",
    "RadarFrame",
    "SignalProcessor",
    "build_mock_processed_frame",
    "build_mock_radar_frame",
    "build_mock_sequence",
]
