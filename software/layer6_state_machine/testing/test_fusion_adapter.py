import numpy as np

from software.layer6_state_machine.fusion_adapter import L1L2FusionAdapter


class _Presence:
    presence_raw = 0.7
    motion_raw = 0.5


class _MMW:
    points = [1, 2, 3, 4, 5, 6]


def test_adapter_builds_contract_from_dict_inputs():
    adapter = L1L2FusionAdapter(mmwave_max_points=10)
    raw = {
        "frame_number": 9,
        "timestamp_ms": 111.0,
        "radar_id": "radar_main",
        "mmwave_frame": {"points": [1, 2, 3]},
        "presence_frame": {"presence_raw": 0.4, "motion_raw": 0.2},
        "thermal_presence": 0.8,
    }

    out = adapter.adapt(raw)
    assert out.frame_number == 9
    assert out.source_mode == "provisional_l1_l2"
    assert 0.0 <= out.fused_score <= 1.0
    assert 0.0 <= out.confidence <= 1.0


def test_adapter_handles_object_inputs_and_thermal_frame():
    adapter = L1L2FusionAdapter(mmwave_max_points=6)
    raw = {
        "frame_number": 2,
        "mmwave_frame": _MMW(),
        "presence_frame": _Presence(),
        "thermal_frame_bgr": np.full((12, 12, 3), 120, dtype=np.uint8),
    }

    out = adapter.adapt(raw)
    assert out.evidence["point_count"] == 6.0
    assert out.trigger_score >= 0.7
