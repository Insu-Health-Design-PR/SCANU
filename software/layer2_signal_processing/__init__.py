"""Public API for Layer 2 signal processing."""

from .calibration import BackgroundModel
from .feature_extractor import FeatureExtractor, HeatmapFeatures
from .frame_buffer import FrameBuffer
from .signal_processor import ProcessedFrame, SignalProcessor

__all__ = [
    "BackgroundModel",
    "FeatureExtractor",
    "FrameBuffer",
    "HeatmapFeatures",
    "ProcessedFrame",
    "SignalProcessor",
]
