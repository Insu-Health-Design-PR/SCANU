from software.layer6_state_machine.models import StateEvent, SystemState
from software.layer7_alerts import AlertLevel, AlertManager, EventLogger



def _payload(state: SystemState, frame: int):
    mgr = AlertManager()
    event = StateEvent(
        previous_state=SystemState.IDLE,
        current_state=state,
        reason="test",
        frame_number=frame,
        timestamp_ms=1_700_000_000_000 + frame,
        radar_id="radar_main",
        scores={"fused_score": float(frame), "confidence": 1.0},
    )
    return mgr.build(event)


def test_append_and_recent_ordering():
    log = EventLogger()
    p1 = _payload(SystemState.IDLE, 1)
    p2 = _payload(SystemState.TRIGGERED, 2)
    p3 = _payload(SystemState.FAULT, 3)

    log.append(p1)
    log.append(p2)
    log.append(p3)

    recent = log.recent(limit=2)
    assert len(recent) == 2
    assert recent[0].event_id == p3.event_id
    assert recent[1].event_id == p2.event_id


def test_by_level_filters_correctly():
    log = EventLogger()
    p1 = _payload(SystemState.IDLE, 1)
    p2 = _payload(SystemState.FAULT, 2)
    p3 = _payload(SystemState.FAULT, 3)

    log.append(p1)
    log.append(p2)
    log.append(p3)

    faults = log.by_level(AlertLevel.FAULT, limit=10)
    assert len(faults) == 2
    assert all(item.level == AlertLevel.FAULT for item in faults)
    assert faults[0].event_id == p3.event_id
