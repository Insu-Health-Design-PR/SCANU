from software.layer6_state_machine.models import SystemHealth, SystemState
from software.layer6_state_machine.orchestrator import Layer6Orchestrator


def test_tick_returns_event_snapshot_and_fault_action_request():
    orch = Layer6Orchestrator()

    raw = {
        "frame_number": 1,
        "timestamp_ms": 1.0,
        "mmwave_frame": {"points": [1, 2, 3, 4]},
        "presence_frame": {"presence_raw": 0.6, "motion_raw": 0.6},
    }

    event, snapshot, action = orch.tick(
        raw,
        health=SystemHealth(has_fault=True, fault_code="data_stall", sensor_online_count=1),
    )

    assert event.current_state == SystemState.FAULT
    assert snapshot.state == SystemState.FAULT
    assert action is not None
    assert action.action == "reset_soft"


def test_orchestrator_control_passthrough_manual_guard():
    orch = Layer6Orchestrator()
    blocked = orch.kill_holders("radar_main", manual_confirm=False)
    assert blocked.success is False
