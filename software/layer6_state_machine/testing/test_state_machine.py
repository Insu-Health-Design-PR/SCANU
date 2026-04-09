from software.layer6_state_machine.models import FusionInputContract, StateMachineConfig, SystemHealth, SystemState
from software.layer6_state_machine.state_machine import StateMachine


def _inp(frame: int, fused: float, trigger: float, confidence: float = 0.8) -> FusionInputContract:
    return FusionInputContract(
        frame_number=frame,
        timestamp_ms=float(frame * 10),
        radar_id="radar_main",
        fused_score=fused,
        confidence=confidence,
        trigger_score=trigger,
        anomaly_score=fused,
    )


def test_nominal_progression_idle_to_anomaly():
    sm = StateMachine(StateMachineConfig())

    e1 = sm.update(_inp(1, fused=0.30, trigger=0.40), SystemHealth())
    e2 = sm.update(_inp(2, fused=0.40, trigger=0.42), SystemHealth())
    e3 = sm.update(_inp(3, fused=0.50, trigger=0.50), SystemHealth())
    e4 = sm.update(_inp(4, fused=0.55, trigger=0.52), SystemHealth())
    e5 = sm.update(_inp(5, fused=0.82, trigger=0.80), SystemHealth())
    e6 = sm.update(_inp(6, fused=0.84, trigger=0.80), SystemHealth())

    assert e1.current_state == SystemState.IDLE
    assert e2.current_state == SystemState.TRIGGERED
    assert e4.current_state == SystemState.SCANNING
    assert e6.current_state == SystemState.ANOMALY_DETECTED


def test_fault_priority_and_clear_latch():
    sm = StateMachine(StateMachineConfig())
    sm.update(_inp(1, fused=0.9, trigger=0.9), SystemHealth())

    fault_event = sm.update(_inp(2, fused=0.2, trigger=0.1), SystemHealth(has_fault=True, fault_code="radar_stall"))
    assert fault_event.current_state == SystemState.FAULT

    latched = sm.update(_inp(3, fused=0.1, trigger=0.1), SystemHealth(has_fault=False, fault_clear_requested=False))
    assert latched.current_state == SystemState.FAULT

    cleared = sm.update(_inp(4, fused=0.1, trigger=0.1), SystemHealth(has_fault=False, fault_clear_requested=True))
    assert cleared.current_state == SystemState.IDLE


def test_anomaly_hysteresis_hold():
    sm = StateMachine(StateMachineConfig())

    # Enter anomaly first.
    sm.update(_inp(1, fused=0.6, trigger=0.6), SystemHealth())
    sm.update(_inp(2, fused=0.7, trigger=0.7), SystemHealth())
    sm.update(_inp(3, fused=0.85, trigger=0.85), SystemHealth())
    sm.update(_inp(4, fused=0.86, trigger=0.86), SystemHealth())
    assert sm.state == SystemState.ANOMALY_DETECTED

    # A single low frame should not immediately drop anomaly.
    hold = sm.update(_inp(5, fused=0.2, trigger=0.2), SystemHealth())
    assert hold.current_state == SystemState.ANOMALY_DETECTED
