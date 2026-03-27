"""TI mmWave (IWR6843) UART + TLV parsing helpers."""

from .radar_constants import MAGIC_WORD, TLVType
from .radar_config import DEFAULT_CONFIG, RadarConfigurator
from .serial_manager import SerialManager
from .tlv_parser import DetectedPoint, ParsedFrame, TLVParser
from .uart_source import FrameHeader, UARTSource
from .point_filter import RadarPointFilterConfig, filter_detected_points

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
    "RadarPointFilterConfig",
    "filter_detected_points",
]
