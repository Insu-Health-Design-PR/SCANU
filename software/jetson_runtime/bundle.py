"""Frame-bundle creation for Jetson serve mode."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any, Literal

from layer1_sensor_hub.mmwave import load_normalized_mmwave_frames
from layer8_ui import sensor_runner
from layer8_ui.artifact_paths import resolved_artifact_path
from layer8_ui.settings_store import DEFAULT_SETTINGS

from .config import JetsonRuntimeConfig


def _read_jpeg_b64(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    try:
        return base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""


def _image_payload(config: JetsonRuntimeConfig, sensor: Literal["webcam", "thermal"]) -> dict[str, Any]:
    settings = {
        **DEFAULT_SETTINGS,
        **config.layer8_settings,
    }
    sensor_settings = settings.get(sensor) if isinstance(settings.get(sensor), dict) else {}
    live_path = resolved_artifact_path(
        settings,
        relative_to_software=str(sensor_settings.get("live_frame") or ""),
        layer8_dir=config.layer8_dir,
    )
    width_key = "webcam_width" if sensor == "webcam" else "thermal_width"
    height_key = "webcam_height" if sensor == "webcam" else "thermal_height"
    return {
        "jpeg_b64": _read_jpeg_b64(live_path),
        "width": int(sensor_settings.get(width_key) or 0),
        "height": int(sensor_settings.get(height_key) or 0),
    }


def _latest_mmwave(config: JetsonRuntimeConfig) -> dict[str, Any]:
    settings = {
        **DEFAULT_SETTINGS,
        **config.layer8_settings,
    }
    mmwave_settings = settings.get("mmwave") if isinstance(settings.get("mmwave"), dict) else {}
    output_path = resolved_artifact_path(
        settings,
        relative_to_software=str(mmwave_settings.get("output") or ""),
        layer8_dir=config.layer8_dir,
    )
    if output_path is None or not output_path.is_file():
        return {"objects": []}
    frames = load_normalized_mmwave_frames(output_path)
    if not frames:
        return {"objects": []}
    latest = frames[-1].to_dict()
    return {
        "frame_id": latest["frame_id"],
        "timestamp_ms": latest["timestamp_ms"],
        "objects": latest["objects"],
        "object_count": latest["object_count"],
    }


def _latest_layer3(config: JetsonRuntimeConfig) -> dict[str, Any]:
    settings = {
        **DEFAULT_SETTINGS,
        **config.layer8_settings,
    }
    mmwave_settings = settings.get("mmwave") if isinstance(settings.get("mmwave"), dict) else {}
    layer3_path = resolved_artifact_path(
        settings,
        relative_to_software=str(mmwave_settings.get("layer3_output") or ""),
        layer8_dir=config.layer8_dir,
    )
    if layer3_path is None or not layer3_path.is_file():
        return {"features": {}}
    try:
        payload = json.loads(layer3_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"features": {}}
    if isinstance(payload, list) and payload:
        latest = payload[-1] if isinstance(payload[-1], dict) else {}
    elif isinstance(payload, dict):
        latest = payload
    else:
        latest = {}
    return {
        "features": latest.get("features", latest),
    }


def _health(config: JetsonRuntimeConfig) -> dict[str, str]:
    out: dict[str, str] = {}
    for sensor in ("webcam", "thermal", "mmwave"):
        enabled = bool((config.sensors.get(sensor) or {}).get("enabled", True))
        if not enabled:
            out[sensor] = "disabled"
            continue
        status = sensor_runner.status(sensor, config.layer8_dir)
        out[sensor] = "online" if bool(status.get("running")) else "offline"
    return out


def build_frame_bundle(config: JetsonRuntimeConfig, *, frame_id: int | None = None) -> dict[str, Any]:
    """Build the frame-by-frame payload sent from a Jetson to Main in serve mode."""

    mmwave = _latest_mmwave(config)
    resolved_frame_id = int(
        frame_id
        if frame_id is not None
        else mmwave.get("frame_id") or int(time.time() * 1000)
    )
    return {
        "jetson_id": config.jetson_id,
        "mode": config.mode,
        "frame_id": resolved_frame_id,
        "timestamp_ms": int(time.time() * 1000),
        "rgb": _image_payload(config, "webcam"),
        "thermal": _image_payload(config, "thermal"),
        "mmwave": mmwave,
        "layer3": _latest_layer3(config),
        "health": _health(config),
    }
