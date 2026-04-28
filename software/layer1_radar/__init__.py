"""
Layer 1: Radar Control and Data Acquisition

This module handles:
- Serial port discovery and management
- Radar configuration via CLI commands
- Raw frame capture from UART data port
- TLV frame parsing

Hardware: TI IWR6843AOPEVM
"""

from .mmwave.radar_constants import TLVType, MAGIC_WORD
from .mmwave.serial_manager import SerialManager
from .mmwave.radar_config import RadarConfigurator, DEFAULT_CONFIG
from .mmwave.uart_source import UARTSource, FrameHeader
from .mmwave.tlv_parser import TLVParser, DetectedPoint, ParsedFrame
from .thermal.thermal_source import ThermalCameraSource, normalize_thermal_frame

__all__ = [
    'TLVType',
    'MAGIC_WORD',
    'SerialManager',
    'RadarConfigurator',
    'DEFAULT_CONFIG',
    'UARTSource',
    'FrameHeader',
    'TLVParser',
    'DetectedPoint',
    'ParsedFrame',
    "ThermalCameraSource",
    "normalize_thermal_frame",
]

__version__ = '0.1.0'
