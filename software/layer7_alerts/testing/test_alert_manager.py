from software.layer6_state_machine.models import StateEvent, SystemState
from software.layer7_alerts import AlertLevel, AlertManager



def _event(state: SystemState, frame: int = 1) -> StateEvent:
    return StateEvent(
        previous_state=SystemState.IDLE,
        current_state=state,
        reason="test",
        frame_number=frame,
        timestamp_ms=1_775_759_639_252.0,
        radar_id="radar_main",
        scores={"fused_score": 0.5, "confidence": 0.9},
    )


def test_state_to_level_mapping():
    mgr = AlertManager()

    assert mgr.build(_event(SystemState.IDLE)).level == AlertLevel.INFO
    assert mgr.build(_event(SystemState.TRIGGERED)).level == AlertLevel.WARNING
    assert mgr.build(_event(SystemState.SCANNING)).level == AlertLevel.WARNING
    assert mgr.build(_event(SystemState.ANOMALY_DETECTED)).level == AlertLevel.ALERT
    assert mgr.build(_event(SystemState.FAULT)).level == AlertLevel.FAULT


def test_payload_has_minimum_schema_fields():
    mgr = AlertManager()
    payload = mgr.build(_event(SystemState.TRIGGERED))

    assert payload.event_id.startswith("evt_")
    assert payload.timestamp_utc.endswith("Z")
    assert payload.state == "TRIGGERED"
    assert payload.radar_id == "radar_main"
    assert "fused_score" in payload.scores
    assert payload.message
