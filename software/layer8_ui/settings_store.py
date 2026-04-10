"""JSON settings for Layer 8 sensor dashboard."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    "software_root": "",
    "thermal": {
        "frames": 300,
        "fps": 10.0,
        "video": "layer8_ui/artifacts/thermal_only.mp4",
        "live_frame": "layer8_ui/artifacts/live_thermal.jpg",
        "output": "",
        "thermal_device": 1,
        "thermal_auto_detect": 1,
        "thermal_detect_max_index": 6,
        "thermal_detect_retry_s": 12.0,
        "thermal_width": 160,
        "thermal_height": 120,
        "thermal_fps": 9,
        "panel_w": 640,
        "panel_h": 480,
        "thermal_inference_enabled": 0,
        "thermal_inference_every_n": 3,
        "thermal_inference_threshold": 0.25,
        "thermal_inference_device": -1,
        "thermal_inference_model_id": "",
        "thermal_classifier_enabled": 1,
        "thermal_classifier_weights": "/home/insu/Desktop/l4_safe_unsafe_jpg/best.pt",
        "thermal_classifier_every_n": 5,
        "thermal_classifier_device": -1,
    },
    "infineon": {
        "frames": 300,
        "fps": 10.0,
        "video": "layer8_ui/artifacts/infineon_only.mp4",
        "live_frame": "layer8_ui/artifacts/live_infineon.jpg",
        "output": "",
        "panel_w": 640,
        "panel_h": 480,
        "infineon_uuid": "",
        "verbose": False,
    },
    "mmwave": {
        "frames": 300,
        "mmwave_only": 1,
        "config": "layer1_radar/examples/configs/stable_tracking_indoor2_low_uart.cfg",
        "cli_port": "/dev/ttyUSB0",
        "data_port": "/dev/ttyUSB1",
        "video": "layer1_radar/examples/latest_test.mp4",
        "live_frame": "layer8_ui/artifacts/live_mmwave.jpg",
        "output": "layer8_ui/artifacts/mmwave_frames.json",
        "no_frame_timeout_s": 30.0,
        "verbose": False,
        "extra_args": "",
    },
}


def settings_path(layer8_dir: Path) -> Path:
    return layer8_dir / "ui_settings.json"


def load(layer8_dir: Path) -> dict[str, Any]:
    path = settings_path(layer8_dir)
    if not path.is_file():
        data = deepcopy(DEFAULT_SETTINGS)
        save(layer8_dir, data)
        return data
    with open(path) as f:
        merged = deepcopy(DEFAULT_SETTINGS)
        user = json.load(f)
        if isinstance(user, dict):
            merged.update({k: v for k, v in user.items() if k in ("software_root",)})
            for key in ("thermal", "infineon", "mmwave"):
                if key in user and isinstance(user[key], dict):
                    merged[key] = {**merged[key], **user[key]}
        return merged


def save(layer8_dir: Path, data: dict[str, Any]) -> None:
    path = settings_path(layer8_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)
