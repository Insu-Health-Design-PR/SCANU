"""Layer 6 deterministic state machine."""

from __future__ import annotations

import time

from .models import (
    FusionInputContract,
    StateEvent,
    StateMachineConfig,
    StateSnapshot,
    SystemHealth,
    SystemState,
)


class StateMachine:
    """State orchestrator with fixed priority and hysteresis counters."""

    def __init__(self, config: StateMachineConfig | None = None) -> None:
        self._config = config if config is not None else StateMachineConfig()
        self._state = SystemState.IDLE
        now_ms = time.time() * 1000.0
        self._entered_at_ms = now_ms
        self._last_timestamp_ms = now_ms

        self._trigger_frames = 0
        self._scan_frames = 0
        self._anomaly_enter_frames = 0
        self._anomaly_exit_frames = 0

        self._last_input: FusionInputContract | None = None
        self._last_health = SystemHealth()

    @property
    def state(self) -> SystemState:
        return self._state

    def _transition(self, next_state: SystemState, *, reason: str, inp: FusionInputContract, now_ms: float) -> StateEvent:
        previous = self._state
        if next_state != previous:
            self._state = next_state
            self._entered_at_ms = now_ms

        self._last_timestamp_ms = now_ms
        return StateEvent(
            previous_state=previous,
            current_state=self._state,
            reason=reason,
            frame_number=inp.frame_number,
            timestamp_ms=inp.timestamp_ms,
            radar_id=inp.radar_id,
            scores={
                "fused_score": float(inp.fused_score),
                "confidence": float(inp.confidence),
                "trigger_score": float(inp.trigger_score),
                "anomaly_score": float(inp.anomaly_score),
            },
        )

    def _update_counters(self, inp: FusionInputContract) -> None:
        cfg = self._config

        is_trigger = inp.trigger_score >= cfg.trigger_threshold
        is_scan = inp.fused_score >= cfg.scan_threshold or is_trigger
        is_anomaly_enter = inp.fused_score >= cfg.anomaly_threshold and inp.confidence >= cfg.minimum_confidence
        is_anomaly_exit = inp.fused_score < cfg.anomaly_exit_threshold

        self._trigger_frames = self._trigger_frames + 1 if is_trigger else 0
        self._scan_frames = self._scan_frames + 1 if is_scan else 0
        self._anomaly_enter_frames = self._anomaly_enter_frames + 1 if is_anomaly_enter else 0
        self._anomaly_exit_frames = self._anomaly_exit_frames + 1 if is_anomaly_exit else 0

    def _desired_non_fault_state(self, inp: FusionInputContract) -> tuple[SystemState, str]:
        cfg = self._config

        # Hold anomaly until a stable exit condition is observed.
        if self._state == SystemState.ANOMALY_DETECTED and self._anomaly_exit_frames < cfg.anomaly_exit_frames:
            return (SystemState.ANOMALY_DETECTED, "anomaly_hysteresis_hold")

        if (
            self._anomaly_enter_frames >= cfg.anomaly_enter_frames
            and self._scan_frames >= cfg.scan_min_frames
        ):
            return (SystemState.ANOMALY_DETECTED, "anomaly_threshold_met")

        if self._scan_frames >= cfg.scan_min_frames:
            return (SystemState.SCANNING, "scan_window_active")

        if self._trigger_frames >= cfg.trigger_enter_frames:
            return (SystemState.TRIGGERED, "trigger_detected")

        return (SystemState.IDLE, "activity_low")

    def update(
        self,
        inp: FusionInputContract,
        health: SystemHealth,
        now_ms: float | None = None,
    ) -> StateEvent:
        """Update state from fusion and health inputs."""

        ts = float(inp.timestamp_ms if now_ms is None else now_ms)
        self._last_input = inp
        self._last_health = health

        self._update_counters(inp)

        # FAULT priority and recovery semantics.
        if health.has_fault:
            return self._transition(
                SystemState.FAULT,
                reason=f"fault:{health.fault_code or 'unknown'}",
                inp=inp,
                now_ms=ts,
            )

        if self._state == SystemState.FAULT:
            if health.fault_clear_requested:
                self._trigger_frames = 0
                self._scan_frames = 0
                self._anomaly_enter_frames = 0
                self._anomaly_exit_frames = 0
                return self._transition(SystemState.IDLE, reason="fault_cleared", inp=inp, now_ms=ts)
            return self._transition(SystemState.FAULT, reason="fault_latched", inp=inp, now_ms=ts)

        desired_state, reason = self._desired_non_fault_state(inp)
        return self._transition(desired_state, reason=reason, inp=inp, now_ms=ts)

    def snapshot(self, now_ms: float | None = None) -> StateSnapshot:
        """Return latest state snapshot for Layer 8/UI."""

        ts = self._last_timestamp_ms if now_ms is None else float(now_ms)
        dwell_ms = max(0.0, ts - self._entered_at_ms)

        last = self._last_input
        health = self._last_health
        fused_score = float(last.fused_score) if last is not None else 0.0
        confidence = float(last.confidence) if last is not None else 0.0
        active_radars = (last.radar_id,) if last is not None else tuple()

        return StateSnapshot(
            state=self._state,
            dwell_ms=dwell_ms,
            fused_score=fused_score,
            confidence=confidence,
            health={
                "has_fault": health.has_fault,
                "fault_code": health.fault_code,
                "sensor_online_count": health.sensor_online_count,
            },
            active_radars=active_radars,
        )
