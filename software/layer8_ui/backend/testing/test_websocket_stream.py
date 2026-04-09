from software.layer6_state_machine.models import ControlResult, StateEvent, StateSnapshot, SystemState
from software.layer7_alerts import AlertManager
from software.layer8_ui.websocket_stream import WebSocketStream



def test_encode_status_event_type():
    snapshot = StateSnapshot(
        state=SystemState.IDLE,
        dwell_ms=10.0,
        fused_score=0.2,
        confidence=0.8,
        health={"has_fault": False, "sensor_online_count": 1},
        active_radars=("radar_main",),
    )
    encoded = WebSocketStream.encode_status(snapshot)
    assert encoded["event_type"] == "status_update"
    assert encoded["payload"]["state"] == "IDLE"



def test_encode_alert_event_type():
    event = StateEvent(
        previous_state=SystemState.IDLE,
        current_state=SystemState.FAULT,
        reason="fault",
        frame_number=1,
        timestamp_ms=1_700_000_000_000,
        radar_id="radar_main",
        scores={"fused_score": 0.1, "confidence": 0.7},
    )
    alert = AlertManager().build(event)
    encoded = WebSocketStream.encode_alert(alert)
    assert encoded["event_type"] == "alert_event"
    assert encoded["payload"]["state"] == "FAULT"



def test_encode_control_result_event_type():
    result = ControlResult(
        radar_id="radar_main",
        action="reset_soft",
        success=True,
        message="ok",
        details={"x": 1},
    )
    encoded = WebSocketStream.encode_control_result(result)
    assert encoded["event_type"] == "control_result"
    assert encoded["payload"]["action"] == "reset_soft"


def test_encode_visual_update_event_type():
    encoded = WebSocketStream.encode_visual_update({"source_mode": "simulate", "point_cloud": []})
    assert encoded["event_type"] == "visual_update"
    assert encoded["payload"]["source_mode"] == "simulate"
