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
    },
    "webcam": {
        "frames": 0,
        "fps": 10.0,
        "video": "layer8_ui/artifacts/webcam_weapon.mp4",
        "live_frame": "layer8_ui/artifacts/live_webcam.jpg",
        "output": "",
        "webcam_device": 0,
        "webcam_width": 1920,
        "webcam_height": 1080,
        "metrics_json": "layer8_ui/artifacts/live_threat_metrics.json",
        "active_model_profile_id": "",
        "weapon_checkpoint": "layer4_inference/trained_models/gun_detection/gun_prob_best.pt",
        "person_detection_model": "yolov8n.pt",
        "weapon_unsafe_threshold": 0.5,
        "weapon_gun_threshold": 0.0,
        "weapon_yolo_model": "yolov8n.pt",
        "weapon_conf": 0.25,
        "weapon_image_size": 224,
        "weapon_gun_conf": 0.25,
        "weapon_gun_imgsz": 640,
        "weapon_min_box_px": 24,
        "weapon_gun_min_box_px": 8,
        "weapon_gun_thermal": 0,
        "weapon_no_gun_yolo": 0,
        "weapon_show_yolo_name": 0,
        "weapon_gun_yolo_model": "",
        "weapon_extra_args": "",
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
            if (
                "webcam" not in user
                and "infineon" in user
                and isinstance(user.get("infineon"), dict)
            ):
                merged["webcam"] = {**merged["webcam"], **user["infineon"]}
            for key in ("thermal", "webcam", "mmwave"):
                if key in user and isinstance(user[key], dict):
                    merged[key] = {**merged[key], **user[key]}
        return merged


def reset_webcam_weapon_defaults(layer8_dir: Path) -> dict[str, Any]:
    """Reset only ``weapon_*`` and ``verbose`` under ``webcam`` (Model tab); paths/frames unchanged."""
    data = load(layer8_dir)
    defs = deepcopy(DEFAULT_SETTINGS["webcam"])
    w = {**(data.get("webcam") or {})}
    for k, v in defs.items():
        if k.startswith("weapon_") or k in ("verbose", "person_detection_model"):
            w[k] = v
    data["webcam"] = w
    save(layer8_dir, data)
    return load(layer8_dir)


def save(layer8_dir: Path, data: dict[str, Any]) -> None:
    path = settings_path(layer8_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)
