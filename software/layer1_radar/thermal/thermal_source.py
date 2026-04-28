"""
Compatibility shim for thermal helpers in layer1_radar.

The implementation now lives in ``layer1_sensor_hub.thermal.thermal_source``.
Re-export the same symbols so existing ``layer1_radar`` imports keep working.
"""

from layer1_sensor_hub.thermal.thermal_source import (  # noqa: F401
    ThermalCameraSource,
    ThermalFrameInfo,
    normalize_thermal_frame,
)

__all__ = [
    "ThermalCameraSource",
    "ThermalFrameInfo",
    "normalize_thermal_frame",
]

