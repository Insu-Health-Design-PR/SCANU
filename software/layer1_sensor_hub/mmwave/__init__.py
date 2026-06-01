"""TI mmWave (IWR6843) UART + TLV parsing helpers."""

from .radar_constants import MAGIC_WORD, TLVType
from .radar_config import DEFAULT_CONFIG, RadarConfigurator
from .serial_manager import SerialManager
from .tlv_parser import DetectedPoint, ParsedFrame, TLVParser
from .uart_source import FrameHeader, UARTSource
from .normalized import (
    NormalizedMmwaveFrame,
    NormalizedMmwaveObject,
    dump_normalized_mmwave_frames,
    load_normalized_mmwave_frames,
    normalize_mmwave_frame,
    normalize_mmwave_frames,
    normalize_mmwave_object,
)
from .visualization import (
    CameraProjectionConfig,
    MovementTrailTracker,
    project_frame_to_camera,
    render_mmwave_camera_overlay,
    render_top_down_jpeg,
)
from .zone_config import ZoneConfig, ZoneAlert, ZoneMonitor
from .heatmap import HeatmapConfig, HeatmapGenerator

__all__ = [
    "TLVType",
    "MAGIC_WORD",
    "SerialManager",
    "RadarConfigurator",
    "DEFAULT_CONFIG",
    "UARTSource",
    "FrameHeader",
    "TLVParser",
    "DetectedPoint",
    "ParsedFrame",
    "NormalizedMmwaveFrame",
    "NormalizedMmwaveObject",
    "normalize_mmwave_object",
    "normalize_mmwave_frame",
    "normalize_mmwave_frames",
    "load_normalized_mmwave_frames",
    "dump_normalized_mmwave_frames",
    "CameraProjectionConfig",
    "MovementTrailTracker",
    "project_frame_to_camera",
    "render_mmwave_camera_overlay",
    "render_top_down_jpeg",
    "ZoneConfig",
    "ZoneAlert",
    "ZoneMonitor",
    "HeatmapConfig",
    "HeatmapGenerator",
]
