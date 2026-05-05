"""Public API for Layer 6 state and control plane."""

from .fusion_adapter import L1L2FusionAdapter  # deprecated — use layer5_fusion
from .models import (
    ActionRequest,
    ControlResult,
    RadarRuntimeSpec,
    SensorStatus,
    StateEvent,
    StateMachineConfig,
    StateSnapshot,
    SystemHealth,
    SystemState,
    WeaponStateMachineConfig,
)
from .orchestrator import Layer6Orchestrator
from .sensor_control import SensorControlManager
from .state_machine import StateMachine

from layer5_fusion.models import FusionInputContract  # canonical home

__all__ = [
    "ActionRequest",
    "ControlResult",
    "FusionInputContract",
    "L1L2FusionAdapter",
    "Layer6Orchestrator",
    "RadarRuntimeSpec",
    "SensorControlManager",
    "SensorStatus",
    "StateEvent",
    "StateMachine",
    "StateMachineConfig",
    "StateSnapshot",
    "SystemHealth",
    "SystemState",
    "WeaponStateMachineConfig",
]
