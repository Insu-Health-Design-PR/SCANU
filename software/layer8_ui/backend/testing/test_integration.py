from software.layer6_state_machine.models import ActionRequest, StateEvent, StateSnapshot, SystemState
from software.layer7_alerts import AlertManager
from software.layer8_ui.backend.integration import L6L7ToL8Bridge



def test_bridge_ingest_publishes_status_alert_fault():
    bridge = L6L7ToL8Bridge()
    queue = bridge.publisher.subscribe()

    snapshot = StateSnapshot(
        state=SystemState.FAULT,
        dwell_ms=50.0,
        fused_score=0.2,
        confidence=0.8,
        health={"has_fault": True, "fault_code": "sensor_timeout", "sensor_online_count": 1},
        active_radars=("radar_main",),
    )
    event = StateEvent(
        previous_state=SystemState.SCANNING,
        current_state=SystemState.FAULT,
        reason="sensor_timeout",
        frame_number=9,
        timestamp_ms=1_700_000_000_000,
        radar_id="radar_main",
        scores={"fused_score": 0.2, "confidence": 0.8},
    )
    alert = AlertManager().build(event)
    action = ActionRequest(radar_id="radar_main", action="reset_soft", reason="sensor_timeout")

    bridge.ingest(snapshot=snapshot, alert=alert, action_request=action, now_ms=1_700_000_000_000)

    events = [queue.get_nowait(), queue.get_nowait(), queue.get_nowait(), queue.get_nowait()]
    event_types = [item["event_type"] for item in events]

    assert "status_update" in event_types
    assert "alert_event" in event_types
    assert "sensor_fault" in event_types
    assert "heartbeat" in event_types
