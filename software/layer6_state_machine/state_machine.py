"""State machine contracts for Layer 6."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from software.layer5_fusion import FusionResult


class SystemState(str, Enum):
    """Top-level system states."""

    IDLE = "IDLE"
    TRIGGERED = "TRIGGERED"
    SCANNING = "SCANNING"
    ALERT = "ALERT"
    FAULT = "FAULT"


@dataclass(frozen=True, slots=True)
class StateEvent:
    """State transition event emitted at each step."""

    previous_state: SystemState
    current_state: SystemState
    reason: str


class StateMachine:
    """Deterministic transition engine from fused score to system state."""

    def __init__(self, alert_threshold: float = 0.5) -> None:
        self.alert_threshold = alert_threshold
        self.state = SystemState.IDLE

    def step(self, fusion: FusionResult, has_fault: bool = False) -> StateEvent:
        previous = self.state

        if has_fault:
            current = SystemState.FAULT
            reason = "fault flag active"
        elif fusion.fused_score >= self.alert_threshold:
            current = SystemState.ALERT
            reason = f"fused_score {fusion.fused_score:.3f} >= {self.alert_threshold:.3f}"
        elif fusion.fused_score > 0.0:
            if previous in (SystemState.IDLE, SystemState.FAULT):
                current = SystemState.TRIGGERED
                reason = "non-zero fused score detected"
            else:
                current = SystemState.SCANNING
                reason = "continuing scan with low score"
        else:
            current = SystemState.IDLE
            reason = "no activity"

        self.state = current
        return StateEvent(previous_state=previous, current_state=current, reason=reason)
