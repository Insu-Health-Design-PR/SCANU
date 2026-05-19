import json

from software.layer1_sensor_hub.mmwave.normalized import (
    load_normalized_mmwave_frames,
    normalize_mmwave_frame,
)
from software.layer1_sensor_hub.mmwave.visualization import (
    CameraProjectionConfig,
    project_frame_to_camera,
    render_top_down_jpeg,
)


def test_normalize_legacy_points_contract():
    frame = normalize_mmwave_frame(
        {
            "frame": 7,
            "points": [
                {"x": 1.0, "y": 2.0, "z": 0.5, "doppler": -0.25, "snr": 17.5},
            ],
        }
    )

    payload = frame.to_dict()

    assert payload["frame_id"] == 7
    assert payload["object_count"] == 1
    assert payload["objects"][0]["range_m"] > 0
    assert payload["objects"][0]["velocity_mps"] == -0.25
    assert 0 < payload["objects"][0]["confidence"] <= 1


def test_normalize_empty_or_bad_frame_is_valid():
    frame = normalize_mmwave_frame(None, fallback_frame_id=3)

    assert frame.to_dict()["frame_id"] == 3
    assert frame.to_dict()["objects"] == []


def test_load_normalized_frames_from_file(tmp_path):
    path = tmp_path / "frames.json"
    path.write_text(json.dumps([{"frame": 1, "points": []}, {"frame": 2, "points": [{"x": 0.1, "y": 1.2}]}]))

    frames = load_normalized_mmwave_frames(path)

    assert len(frames) == 2
    assert frames[-1].to_dict()["object_count"] == 1


def test_project_frame_to_camera_and_render_preview(tmp_path):
    frame = normalize_mmwave_frame({"frame": 1, "points": [{"x": 0.0, "y": 2.0, "snr": 20.0}]})
    cfg = CameraProjectionConfig(width=640, height=480)

    overlay = project_frame_to_camera(frame, cfg)
    out = tmp_path / "live_mmwave.jpg"
    render_top_down_jpeg(frame, out)

    assert overlay["points"][0]["x_px"] == 320
    assert 0 <= overlay["points"][0]["y_px"] <= 480
    assert out.is_file()
    assert out.stat().st_size > 0
