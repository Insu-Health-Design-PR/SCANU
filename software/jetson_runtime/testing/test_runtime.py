import base64
import json
from pathlib import Path

from jetson_runtime import build_frame_bundle, load_config, mode_layers
from jetson_runtime.main_client import MainClient
from jetson_runtime.runtime import run_once


def _write_config(tmp_path: Path, *, mode: str = "serve") -> Path:
    layer8_dir = tmp_path / "layer8_ui"
    artifacts = layer8_dir / "artifacts"
    artifacts.mkdir(parents=True)
    path = tmp_path / "jetson.json"
    path.write_text(
        json.dumps(
            {
                "jetson_id": "jetson-test",
                "mode": mode,
                "main_url": "http://main.test",
                "software_root": str(tmp_path),
                "layer8_dir": str(layer8_dir),
                "artifacts_dir": str(artifacts),
                "sensors": {
                    "webcam": {"enabled": True},
                    "thermal": {"enabled": True},
                    "mmwave": {"enabled": True},
                },
                "layer8_settings": {
                    "webcam": {
                        "live_frame": "layer8_ui/artifacts/live_webcam.jpg",
                        "webcam_width": 640,
                        "webcam_height": 360,
                    },
                    "thermal": {
                        "live_frame": "layer8_ui/artifacts/live_thermal.jpg",
                        "thermal_width": 160,
                        "thermal_height": 120,
                    },
                    "mmwave": {
                        "output": "layer8_ui/artifacts/mmwave_frames.json",
                        "layer3_output": "layer8_ui/artifacts/layer3_features.json",
                    },
                },
            }
        )
    )
    return path


def test_load_config_and_mode_layers(tmp_path):
    config = load_config(_write_config(tmp_path))

    assert config.jetson_id == "jetson-test"
    assert config.mode == "serve"
    assert mode_layers("serve") == (1, 2, 3, 8)
    assert mode_layers("local") == (1, 2, 3, 4, 5, 6, 7, 8)


def test_build_frame_bundle_from_fixtures(tmp_path):
    config = load_config(_write_config(tmp_path))
    artifacts = config.layer8_dir / "artifacts"
    (artifacts / "live_webcam.jpg").write_bytes(b"rgb")
    (artifacts / "live_thermal.jpg").write_bytes(b"thermal")
    (artifacts / "mmwave_frames.json").write_text(
        json.dumps(
            [
                {
                    "frame_id": 120,
                    "timestamp_ms": 123,
                    "objects": [{"x": 1.0, "y": 2.0, "velocity_mps": 0.5, "snr": 21}],
                }
            ]
        )
    )
    (artifacts / "layer3_features.json").write_text(json.dumps([{"features": {"risk": 0.2}}]))

    bundle = build_frame_bundle(config)

    assert bundle["jetson_id"] == "jetson-test"
    assert bundle["mode"] == "serve"
    assert bundle["frame_id"] == 120
    assert bundle["rgb"]["jpeg_b64"] == base64.b64encode(b"rgb").decode("ascii")
    assert bundle["thermal"]["jpeg_b64"] == base64.b64encode(b"thermal").decode("ascii")
    assert bundle["mmwave"]["object_count"] == 1
    assert bundle["layer3"]["features"] == {"risk": 0.2}


def test_local_mode_activates_layers_1_to_8(tmp_path):
    config = load_config(_write_config(tmp_path, mode="local"))

    snapshot = run_once(config, send=False)

    assert snapshot.mode == "local"
    assert snapshot.active_layers == (1, 2, 3, 4, 5, 6, 7, 8)
    assert snapshot.frame_bundle is None


def test_main_client_posts_register_heartbeat_and_frames(monkeypatch, tmp_path):
    config = load_config(_write_config(tmp_path))
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(req, timeout):
        calls.append((req.full_url, req.data, timeout))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = MainClient(config)

    assert client.register()["ok"] is True
    assert client.heartbeat({"webcam": "online"})["ok"] is True
    assert client.send_frame({"frame_id": 1})["ok"] is True
    assert calls[0][0].endswith("/api/jetsons/register")
    assert calls[1][0].endswith("/api/jetsons/jetson-test/heartbeat")
    assert calls[2][0].endswith("/api/jetsons/jetson-test/frames")
