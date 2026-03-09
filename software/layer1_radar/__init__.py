"""
Layer 1: Radar Control and Data Acquisition

This module handles:
- Serial port discovery and management
- Radar configuration via CLI commands
- Raw frame capture from UART data port
- TLV frame parsing

Hardware: TI IWR6843AOPEVM
"""

from .radar_constants import TLVType, MAGIC_WORD
from .serial_manager import SerialManager
from .radar_config import RadarConfigurator, DEFAULT_CONFIG
from .uart_source import UARTSource, FrameHeader
from .tlv_parser import TLVParser, DetectedPoint, ParsedFrame

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
]

__version__ = '0.1.0'
