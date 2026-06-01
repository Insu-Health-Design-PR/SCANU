"""TI mmWave raw ADC capture helpers for DCA1000EVM.

This package is separate from ``layer1_sensor_hub.mmwave`` because the
standard mmWave module reads processed TLV frames from UART, while this path
captures raw ADC samples through LVDS -> DCA1000 -> Ethernet.
"""

from .adc_reader import AdcCaptureShape, read_adc_data
from .capture_runner import CapturePlan, run_capture_plan
from .dca1000_stream import Dca1000StreamProcessor, StreamResult
from .dca1000_udp import Dca1000NetworkConfig, UdpCaptureResult, UdpDca1000Recorder
from .mmwave_raw_adc_detector import MmwaveDetectionResult, MmweaponCfarParams, RawAdcWeaponDetector, WeaponZoneParams
from .radar_cli import RadarCliConfig, configure_radar_from_file, send_sensor_start, send_sensor_stop

__all__ = [
    "AdcCaptureShape",
    "CapturePlan",
    "Dca1000NetworkConfig",
    "Dca1000StreamProcessor",
    "MmwaveDetectionResult",
    "MmweaponCfarParams",
    "RadarCliConfig",
    "RawAdcWeaponDetector",
    "StreamResult",
    "UdpCaptureResult",
    "UdpDca1000Recorder",
    "WeaponZoneParams",
    "configure_radar_from_file",
    "read_adc_data",
    "run_capture_plan",
    "send_sensor_start",
    "send_sensor_stop",
]
