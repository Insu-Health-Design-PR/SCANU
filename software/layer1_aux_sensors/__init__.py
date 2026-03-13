"""Layer 1 auxiliary sensor acquisition module."""

from .aux_protocol import AuxProtocol, ParsedMessage
from .aux_source import AuxSensorSource
from .config import AuxHealthConfig, AuxSerialConfig
from .health_monitor import HealthMonitor, HealthStatus
from .sensor_models import AuxFrame, AuxHeartbeat, AuxReading
from .serial_bridge import SerialBridge

__all__ = [
    "AuxFrame",
    "AuxHealthConfig",
    "AuxHeartbeat",
    "AuxProtocol",
    "AuxReading",
    "AuxSensorSource",
    "AuxSerialConfig",
    "HealthMonitor",
    "HealthStatus",
    "ParsedMessage",
    "SerialBridge",
]
