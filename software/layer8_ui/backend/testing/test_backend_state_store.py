from software.layer6_state_machine.models import StateSnapshot, SystemState
from software.layer7_alerts import AlertManager
from software.layer6_state_machine.models import StateEvent
from software.layer8_ui.backend_state_store import BackendStateStore



def test_status_and_health_with_snapshot():
    store = BackendStateStore()
    snapshot = StateSnapshot(
        state=SystemState.SCANNING,
        dwell_ms=123.0,
        fused_score=0.66,
        confidence=0.92,
        health={"has_fault": False, "fault_code": None, "sensor_online_count": 1},
        active_radars=("radar_main",),
    )
    store.update_status(snapshot, now_ms=1_700_000_000_000)

    status = store.status_response()
    assert status["state"] == "SCANNING"
    assert status["active_radars"] == ["radar_main"]

    health = store.health_response()
    assert health["healthy"] is True
    assert health["has_fault"] is False


def test_recent_alerts_order():
    store = BackendStateStore()
    mgr = AlertManager()

    for idx, st in enumerate((SystemState.IDLE, SystemState.TRIGGERED, SystemState.FAULT), start=1):
        event = StateEvent(
            previous_state=SystemState.IDLE,
            current_state=st,
            reason="test",
            frame_number=idx,
            timestamp_ms=1_700_000_000_000 + idx,
            radar_id="radar_main",
            scores={"fused_score": 0.1 * idx, "confidence": 1.0},
        )
        store.publish_alert(mgr.build(event))

    alerts = store.recent_alerts(limit=2)
    assert len(alerts) == 2
    assert alerts[0]["state"] == "FAULT"
    assert alerts[1]["state"] == "TRIGGERED"
