from software.layer6_state_machine.models import ActionRequest, StateEvent, StateSnapshot, SystemState
from software.layer7_alerts import AlertLevel, L6ToL7Bridge



def test_bridge_ingest_builds_and_logs_alert():
    bridge = L6ToL7Bridge()

    event = StateEvent(
        previous_state=SystemState.SCANNING,
        current_state=SystemState.FAULT,
        reason="sensor_timeout",
        frame_number=10,
        timestamp_ms=1_700_000_000_000,
        radar_id="radar_main",
        scores={"fused_score": 0.2, "confidence": 0.8},
    )
    snapshot = StateSnapshot(
        state=SystemState.FAULT,
        dwell_ms=250.0,
        fused_score=0.2,
        confidence=0.8,
        health={"has_fault": True, "fault_code": "sensor_timeout"},
        active_radars=("radar_main",),
    )
    action = ActionRequest(
        radar_id="radar_main",
        action="reset_soft",
        reason="sensor_timeout",
        manual_required=False,
    )

    payload = bridge.ingest(event, snapshot=snapshot, action_request=action)

    assert payload.level == AlertLevel.FAULT
    assert payload.state == "FAULT"
    assert "action_request" in payload.metadata
    assert bridge.logger.count() == 1
