"""Layer 1 unified sensor hub (mmWave + Infineon + thermal + cameras)."""

from .mmwave.radar_constants import TLVType, MAGIC_WORD
from .mmwave.serial_manager import SerialManager
from .mmwave.radar_config import RadarConfigurator, DEFAULT_CONFIG, WPN_CONFIG, WPN_FIRST_START
from .mmwave.uart_source import UARTSource, FrameHeader
from .mmwave.tlv_parser import TLVParser, DetectedPoint, ParsedFrame
from .thermal.thermal_source import ThermalCameraSource, normalize_thermal_frame
from .sensor_hub import HubFrame, MultiSensorHub

__all__ = [
    "TLVType",
    "MAGIC_WORD",
    "SerialManager",
    "RadarConfigurator",
    "DEFAULT_CONFIG",
    "WPN_CONFIG",
    "WPN_FIRST_START",
    "UARTSource",
    "FrameHeader",
    "TLVParser",
    "DetectedPoint",
    "ParsedFrame",
    "ThermalCameraSource",
    "normalize_thermal_frame",
    "MultiSensorHub",
    "HubFrame",
]
