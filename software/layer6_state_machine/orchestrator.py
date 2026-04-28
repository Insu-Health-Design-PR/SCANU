"""Layer 6 orchestrator binding adapter, state machine, and control plane."""

from __future__ import annotations

import time
from typing import Any

from .fusion_adapter import L1L2FusionAdapter
from .models import ActionRequest, ControlResult, StateEvent, StateSnapshot, SystemHealth, SystemState
from .sensor_control import SensorControlManager
from .state_machine import StateMachine


class Layer6Orchestrator:
    """High-level Layer 6 facade for runtime integration."""

    def __init__(
        self,
        *,
        state_machine: StateMachine | None = None,
        sensor_control: SensorControlManager | None = None,
        adapter: L1L2FusionAdapter | None = None,
        primary_radar_id: str = "radar_main",
    ) -> None:
        self._state_machine = state_machine if state_machine is not None else StateMachine()
        self._sensor_control = sensor_control if sensor_control is not None else SensorControlManager()
        self._adapter = adapter if adapter is not None else L1L2FusionAdapter()
        self._primary_radar_id = primary_radar_id

    @property
    def sensor_control(self) -> SensorControlManager:
        return self._sensor_control

    def tick(
        self,
        raw_inputs: Any,
        *,
        health: SystemHealth | None = None,
        now_ms: float | None = None,
        radar_id: str | None = None,
    ) -> tuple[StateEvent, StateSnapshot, ActionRequest | None]:
        """Run one Layer 6 cycle from raw signals to state outputs."""

        ts = float(now_ms if now_ms is not None else time.time() * 1000.0)
        rid = radar_id or self._primary_radar_id
        input_contract = self._adapter.adapt(raw_inputs, radar_id=rid, now_ms=ts)

        health_value = health if health is not None else SystemHealth()
        event = self._state_machine.update(input_contract, health_value, now_ms=ts)
        snapshot = self._state_machine.snapshot(now_ms=ts)

        action = self._suggest_action(event=event, health=health_value)
        return (event, snapshot, action)

    def _suggest_action(self, *, event: StateEvent, health: SystemHealth) -> ActionRequest | None:
        if event.current_state == SystemState.FAULT and health.has_fault:
            return ActionRequest(
                radar_id=event.radar_id,
                action="reset_soft",
                reason=health.fault_code or "fault_detected",
                manual_required=False,
            )
        return None

    # Control-plane passthroughs
    def get_status(self, radar_id: str) -> Any:
        return self._sensor_control.get_status(radar_id)

    def apply_config(self, radar_id: str, *, config_path: str | None = None, config_text: str | None = None) -> ControlResult:
        return self._sensor_control.apply_config(radar_id, config_path=config_path, config_text=config_text)

    def reset_soft(self, radar_id: str) -> ControlResult:
        return self._sensor_control.reset_soft(radar_id)

    def kill_holders(self, radar_id: str, *, force: bool = False, manual_confirm: bool = False) -> ControlResult:
        return self._sensor_control.kill_holders(radar_id, force=force, manual_confirm=manual_confirm)

    def usb_reset(self, radar_id: str, *, manual_confirm: bool = False) -> ControlResult:
        return self._sensor_control.usb_reset(radar_id, manual_confirm=manual_confirm)
