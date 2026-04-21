"""HTTP + WebSocket routes for the Layer 8 static dashboard (no business rules in ``app``)."""

from __future__ import annotations

import asyncio
import base64
import json
import shutil
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from layer8_ui import sensor_runner, system_metrics, thermal_runner, webcam_runner
from layer8_ui.artifact_paths import resolved_artifact_path, software_root_from_settings
from layer8_ui.preview_media import (
    THERMAL_JPEG_WAITING,
    WEBCAM_JPEG_WAITING,
    mjpeg_headers,
    mjpeg_placeholder_jpeg,
)
from layer8_ui.settings_store import DEFAULT_SETTINGS, load, reset_webcam_weapon_defaults, save

SensorName = Literal["thermal", "webcam", "mmwave"]

MODEL_PROFILE_WEBCAM_KEYS: tuple[str, ...] = (
    "webcam_device",
    "webcam_width",
    "webcam_height",
    "metrics_json",
    "person_detection_model",
    "weapon_yolo_model",
    "weapon_conf",
    "weapon_min_box_px",
    "weapon_show_yolo_name",
    "weapon_unsafe_threshold",
    "weapon_gun_threshold",
    "weapon_image_size",
    "weapon_gun_conf",
    "weapon_gun_imgsz",
    "weapon_gun_min_box_px",
    "weapon_gun_thermal",
    "weapon_no_gun_yolo",
    "weapon_gun_yolo_model",
    "weapon_extra_args",
)


class SettingsBody(BaseModel):
    settings: dict[str, Any]


class ApplyModelProfileBody(BaseModel):
    id: str


class SnapshotModelProfileBody(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    # Optional: current Model + Webcam form state so operators need not Save before "Save to profile".
    values: dict[str, Any] | None = None


class CompatReconfigRequest(BaseModel):
    radar_id: str = "radar_main"
    config_path: str | None = None
    config_text: str | None = None


class CompatResetSoftRequest(BaseModel):
    radar_id: str = "radar_main"


class UiPreferencesPayload(BaseModel):
    appliedLayout: str = "Triple View"
    previewLayout: str = "Triple View"
    focusView: str = "rgb"
    layoutStyle: str = "grid"
    customModules: dict[str, bool] = {}


_PROFILE_FILE_META_KEYS = frozenset({"version", "schema", "__schema__", "_meta"})


def _model_profiles_path(layer8_dir: Path) -> Path:
    return layer8_dir / "profiles" / "model_profiles.json"


def _load_model_profiles_raw(layer8_dir: Path) -> dict[str, Any]:
    p = _model_profiles_path(layer8_dir)
    if not p.is_file():
        return {}
    with open(p) as f:
        raw = json.load(f)
    return raw if isinstance(raw, dict) else {}


def _coerce_profile_entry(pid: str, v: Any) -> dict[str, Any] | None:
    if not isinstance(v, dict):
        return None
    pid_s = str(pid).strip()
    if not pid_s or pid_s in _PROFILE_FILE_META_KEYS:
        return None
    if "values" in v and isinstance(v.get("values"), dict):
        return {
            "label": str(v.get("label") or pid_s),
            "description": str(v.get("description") or ""),
            "values": dict(v["values"]),
        }
    return {"label": pid_s, "description": "", "values": dict(v)}


def _normalize_profiles_document(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """profile_id -> {label, description, values}. Migrates legacy list format."""
    if isinstance(raw.get("profiles"), list):
        out: dict[str, dict[str, Any]] = {}
        for p in raw["profiles"]:
            if not isinstance(p, dict):
                continue
            pid = str(p.get("id") or "").strip()
            if not pid:
                continue
            values = p.get("values") if isinstance(p.get("values"), dict) else p.get("webcam")
            if not isinstance(values, dict):
                values = {}
            out[pid] = {
                "label": str(p.get("label") or p.get("name") or pid),
                "description": str(p.get("description") or ""),
                "values": dict(values),
            }
        return out
    if isinstance(raw.get("profiles"), dict):
        out = {}
        for pid, v in raw["profiles"].items():
            ent = _coerce_profile_entry(pid, v)
            if ent:
                out[str(pid)] = ent
        return out
    out = {}
    for k, v in raw.items():
        if k in _PROFILE_FILE_META_KEYS:
            continue
        ent = _coerce_profile_entry(k, v)
        if ent:
            out[str(k)] = ent
    return out


def _serialize_profiles_to_disk(norm: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """On-disk shape: { profile_id: { label, description, values } }."""
    disk: dict[str, Any] = {}
    for pid, entry in norm.items():
        disk[pid] = {
            "label": entry.get("label", pid),
            "description": entry.get("description", ""),
            "values": dict(entry.get("values") or {}),
        }
    return disk


def _extract_profile_values(webcam: dict[str, Any]) -> dict[str, Any]:
    return {k: webcam[k] for k in MODEL_PROFILE_WEBCAM_KEYS if k in webcam}


def _apply_values_to_webcam(webcam: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    merged = {**webcam, **values}
    pm = merged.get("person_detection_model")
    if pm is not None and str(pm).strip():
        merged["weapon_yolo_model"] = str(pm).strip()
    return merged


def _get_model_profiles_normalized(layer8_dir: Path) -> dict[str, dict[str, Any]]:
    return _normalize_profiles_document(_load_model_profiles_raw(layer8_dir))


def _save_model_profiles(layer8_dir: Path, data: dict[str, Any]) -> None:
    p = _model_profiles_path(layer8_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_file():
        bak = p.with_suffix(".json.bak")
        try:
            shutil.copy2(p, bak)
        except OSError:
            pass
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(p)


def _ui_prefs_path(layer8_dir: Path) -> Path:
    return layer8_dir / "ui_prefs.json"


def _default_ui_prefs() -> dict[str, Any]:
    return {
        "appliedLayout": "Triple View",
        "previewLayout": "Triple View",
        "focusView": "rgb",
        "layoutStyle": "grid",
        "customModules": {
            "rgb": True,
            "thermal": True,
            "pointCloud": True,
            "presence": True,
            "systemStatus": True,
            "execution": True,
            "consoleLog": True,
        },
    }


def _load_ui_prefs(layer8_dir: Path) -> dict[str, Any]:
    p = _ui_prefs_path(layer8_dir)
    base = _default_ui_prefs()
    if not p.is_file():
        return base
    try:
        raw = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return base
    if not isinstance(raw, dict):
        return base
    merged = {**base, **raw}
    custom = raw.get("customModules")
    if isinstance(custom, dict):
        merged["customModules"] = {**base["customModules"], **custom}
    return merged


def _save_ui_prefs(layer8_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    p = _ui_prefs_path(layer8_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    normalized = _default_ui_prefs()
    normalized.update({k: payload[k] for k in ("appliedLayout", "previewLayout", "focusView", "layoutStyle") if k in payload})
    custom = payload.get("customModules")
    if isinstance(custom, dict):
        normalized["customModules"] = {**normalized["customModules"], **custom}
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(normalized, indent=2))
    tmp.replace(p)
    return normalized


def build_router(layer8_dir: Path) -> APIRouter:
    layer8_dir = Path(layer8_dir).resolve()
    thermal_stream = thermal_runner.get_thermal_shared_stream(layer8_dir)
    webcam_stream = webcam_runner.get_webcam_shared_stream(layer8_dir)
    router = APIRouter()

    def _iso_now() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _sensor_statuses() -> dict[str, dict[str, Any]]:
        return {name: sensor_runner.status(name, layer8_dir) for name in ("thermal", "webcam", "mmwave")}

    def _read_metrics() -> dict[str, Any]:
        s = load(layer8_dir)
        rel = (s.get("webcam") or {}).get("metrics_json") or "layer8_ui/artifacts/live_threat_metrics.json"
        path = resolved_artifact_path(s, relative_to_software=str(rel), layer8_dir=layer8_dir)
        base: dict[str, Any] = {
            "unsafe_pct": None,
            "unsafe_score": None,
            "gun_detected": None,
            "persons_with_gun": None,
            "persons_total": None,
            "prediction": None,
            "mmwave_torso_score": None,
            "frame": None,
            "ts": None,
            "note": "Start the webcam runner; infer_thermal_objects writes webcam.metrics_json each frame.",
        }
        if path is None or not path.is_file():
            return base
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return {**base, "note": "Metrics file exists but is not valid JSON yet."}
        if not isinstance(data, dict):
            return {**base, "note": "Metrics JSON must be an object."}
        out = {**base}
        for k in (
            "unsafe_pct",
            "unsafe_score",
            "gun_detected",
            "persons_with_gun",
            "persons_total",
            "prediction",
            "mmwave_torso_score",
            "frame",
            "ts",
        ):
            if k in data:
                out[k] = data[k]
        out["note"] = ""
        return out

    def _status_payload() -> dict[str, Any]:
        statuses = _sensor_statuses()
        online_count = sum(1 for s in statuses.values() if bool(s.get("running")))
        metrics = _read_metrics()
        confidence = 0.0
        if isinstance(metrics.get("unsafe_score"), (int, float)):
            confidence = float(metrics["unsafe_score"])
        elif isinstance(metrics.get("unsafe_pct"), (int, float)):
            confidence = max(0.0, min(1.0, float(metrics["unsafe_pct"]) / 100.0))
        has_fault = online_count == 0
        return {
            "state": "SCANNING" if online_count > 0 else "IDLE",
            "fused_score": confidence,
            "confidence": confidence,
            "health": {
                "has_fault": has_fault,
                "sensor_online_count": online_count,
            },
            "active_radars": ["radar_main"] if bool(statuses.get("mmwave", {}).get("running")) else [],
        }

    def _health_payload() -> dict[str, Any]:
        status = _status_payload()
        online_count = int(status["health"]["sensor_online_count"])
        has_fault = bool(status["health"]["has_fault"])
        return {
            "healthy": online_count > 0 and not has_fault,
            "has_fault": has_fault,
            "sensor_online_count": online_count,
        }

    def _read_live_jpeg_b64(sensor: Literal["thermal", "webcam"]) -> str | None:
        s = load(layer8_dir)
        runner_on = bool(sensor_runner.status(sensor, layer8_dir).get("running"))
        rel = (s.get(sensor) or {}).get("live_frame") or ""
        path = resolved_artifact_path(s, relative_to_software=str(rel), layer8_dir=layer8_dir)

        raw: bytes | None = None
        if runner_on and path is not None and path.is_file():
            try:
                raw = path.read_bytes()
            except OSError:
                raw = None
        else:
            if sensor == "thermal":
                raw = thermal_stream.latest_jpg()
            else:
                raw = webcam_stream.latest_jpg()
            if not raw and path is not None and path.is_file():
                try:
                    raw = path.read_bytes()
                except OSError:
                    raw = None
        if not raw:
            return None
        return base64.b64encode(raw).decode("ascii")

    def _read_point_cloud() -> list[dict[str, float]]:
        s = load(layer8_dir)
        rel = (s.get("mmwave") or {}).get("output") or "layer8_ui/artifacts/mmwave_frames.json"
        path = resolved_artifact_path(s, relative_to_software=str(rel), layer8_dir=layer8_dir)
        if path is None or not path.is_file():
            return []
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list) or not payload:
            return []
        frame = payload[-1]
        points = frame.get("points") if isinstance(frame, dict) else []
        if not isinstance(points, list):
            return []
        out: list[dict[str, float]] = []
        for p in points[:512]:
            if not isinstance(p, dict):
                continue
            x = p.get("x", p.get("x_m", p.get("pos_x", 0.0)))
            y = p.get("y", p.get("y_m", p.get("pos_y", 0.0)))
            z = p.get("z", p.get("z_m", p.get("pos_z", 0.0)))
            try:
                out.append({"x": float(x), "y": float(y), "z": float(z)})
            except (TypeError, ValueError):
                continue
        return out

    def _visual_payload() -> dict[str, Any]:
        metrics = _read_metrics()
        statuses = _sensor_statuses()
        online_count = sum(1 for s in statuses.values() if bool(s.get("running")))
        detected = bool(metrics.get("gun_detected")) or (int(metrics.get("persons_total") or 0) > 0)
        confidence = 0.0
        if isinstance(metrics.get("unsafe_score"), (int, float)):
            confidence = float(metrics["unsafe_score"])
        elif isinstance(metrics.get("unsafe_pct"), (int, float)):
            confidence = max(0.0, min(1.0, float(metrics["unsafe_pct"]) / 100.0))
        return {
            "timestamp_ms": int(time.time() * 1000),
            "source_mode": "live" if online_count > 0 else "simulate",
            "rgb_jpeg_b64": _read_live_jpeg_b64("webcam"),
            "thermal_jpeg_b64": _read_live_jpeg_b64("thermal"),
            "point_cloud": _read_point_cloud(),
            "presence": {
                "detected": detected,
                "confidence": confidence,
            },
            "meta": {
                "ready": online_count > 0,
                "rgb_enabled": bool(statuses.get("webcam", {}).get("running")),
                "thermal_enabled": bool(statuses.get("thermal", {}).get("running")),
                "point_cloud_enabled": bool(statuses.get("mmwave", {}).get("running")),
                "presence_enabled": True,
            },
        }

    def _alerts_payload(limit: int = 50) -> dict[str, Any]:
        status = _status_payload()
        health = _health_payload()
        metrics = _read_metrics()
        alerts: list[dict[str, Any]] = []
        if health["has_fault"]:
            alerts.append(
                {
                    "event_id": f"fault-{uuid.uuid4().hex[:8]}",
                    "level": "fault",
                    "timestamp_utc": _iso_now(),
                    "message": "No sensors are currently running.",
                }
            )
        if bool(metrics.get("gun_detected")):
            alerts.append(
                {
                    "event_id": f"warn-{uuid.uuid4().hex[:8]}",
                    "level": "warning",
                    "timestamp_utc": _iso_now(),
                    "message": "Gun-like object detected by webcam inference.",
                }
            )
        if isinstance(metrics.get("note"), str) and metrics["note"]:
            alerts.append(
                {
                    "event_id": f"info-{uuid.uuid4().hex[:8]}",
                    "level": "info",
                    "timestamp_utc": _iso_now(),
                    "message": metrics["note"],
                }
            )
        if not alerts:
            alerts.append(
                {
                    "event_id": f"ok-{uuid.uuid4().hex[:8]}",
                    "level": "info",
                    "timestamp_utc": _iso_now(),
                    "message": f"System state: {status['state']}",
                }
            )
        return {"alerts": alerts[: max(1, int(limit))]}

    def _normalize_route_result(result: Any) -> tuple[bool, Any]:
        if isinstance(result, JSONResponse):
            payload: Any
            try:
                payload = json.loads(result.body.decode("utf-8"))
            except Exception:
                payload = {"ok": False, "error": "invalid_json_response"}
            return bool(payload.get("ok")), payload
        if isinstance(result, dict):
            return bool(result.get("ok")), result
        return False, {"ok": False, "error": "unexpected_result_type"}

    @router.get("/api/system/metrics")
    def get_system_metrics() -> dict[str, Any]:
        """CPU / RAM / optional NVIDIA GPU for the dashboard header."""
        return system_metrics.snapshot()

    @router.get("/api/config")
    def get_config() -> dict[str, Any]:
        return load(layer8_dir)

    @router.put("/api/config")
    def put_config(body: SettingsBody) -> dict[str, Any]:
        if not isinstance(body.settings, dict):
            raise HTTPException(400, "settings must be an object")
        save(layer8_dir, body.settings)
        return load(layer8_dir)

    @router.post("/api/config/reset")
    def reset_config() -> dict[str, Any]:
        save(layer8_dir, deepcopy(DEFAULT_SETTINGS))
        return load(layer8_dir)

    @router.post("/api/config/reset/{sensor}")
    def reset_sensor_config(sensor: SensorName) -> dict[str, Any]:
        current = load(layer8_dir)
        current[sensor] = deepcopy(DEFAULT_SETTINGS[sensor])
        save(layer8_dir, current)
        return load(layer8_dir)

    @router.post("/api/config/reset/model")
    def reset_model_weapon_defaults() -> dict[str, Any]:
        """Reset weapon / verbose keys only (stored under ``webcam`` in JSON)."""
        return reset_webcam_weapon_defaults(layer8_dir)

    @router.get("/api/model/options")
    def model_options() -> dict[str, Any]:
        s = load(layer8_dir)
        sw = software_root_from_settings(s)
        gun_dir = sw / "layer4_inference" / "trained_models" / "gun_detection"
        checkpoints: list[str] = []
        if gun_dir.is_dir():
            checkpoints = sorted({p.name for p in gun_dir.glob("*.pt")})
        suggestions = ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt"]
        person_yolo_options = sorted(set(checkpoints) | set(suggestions))
        return {
            "gun_checkpoints": checkpoints,
            "person_yolo_suggestions": suggestions,
            "person_yolo_options": person_yolo_options,
        }

    @router.get("/api/model/profiles")
    def get_model_profiles() -> dict[str, Any]:
        return {"profiles": _get_model_profiles_normalized(layer8_dir)}

    @router.put("/api/model/profiles")
    def put_model_profiles(body: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(body, dict):
            raise HTTPException(400, "body must be an object")
        if "profiles" in body and isinstance(body["profiles"], dict):
            norm_in = body["profiles"]
        else:
            norm_in = {k: v for k, v in body.items() if k not in _PROFILE_FILE_META_KEYS}
        norm: dict[str, dict[str, Any]] = {}
        for pid, v in norm_in.items():
            ent = _coerce_profile_entry(pid, v)
            if ent:
                norm[str(pid)] = ent
        _save_model_profiles(layer8_dir, _serialize_profiles_to_disk(norm))
        return {"profiles": _get_model_profiles_normalized(layer8_dir)}

    @router.post("/api/model/profiles/apply")
    def apply_model_profile(body: ApplyModelProfileBody) -> dict[str, Any]:
        pid = body.id.strip()
        if not pid:
            raise HTTPException(400, "id is required")
        norm = _get_model_profiles_normalized(layer8_dir)
        prof = norm.get(pid)
        if prof is None:
            raise HTTPException(404, "profile not found")
        values = prof.get("values") or {}
        if not isinstance(values, dict):
            raise HTTPException(400, "profile.values must be an object")
        current = load(layer8_dir)
        w = _apply_values_to_webcam({**(current.get("webcam") or {})}, values)
        w["active_model_profile_id"] = pid
        current["webcam"] = w
        save(layer8_dir, current)
        return load(layer8_dir)

    @router.post("/api/model/profiles/snapshot")
    def snapshot_model_profile(body: SnapshotModelProfileBody) -> dict[str, Any]:
        pid = body.id.strip()
        if not pid:
            raise HTTPException(400, "id is required")
        s = load(layer8_dir)
        w_prev = s.get("webcam") or {}
        if body.values is not None and isinstance(body.values, dict):
            w_merged = _apply_values_to_webcam(dict(w_prev), body.values)
            snap = _extract_profile_values(w_merged)
        else:
            snap = _extract_profile_values(w_prev)
        norm = _get_model_profiles_normalized(layer8_dir)
        name = (body.name or "").strip() or pid
        desc = (body.description or "").strip()
        prev = norm.get(pid)
        entry: dict[str, Any] = {
            "label": name,
            "description": desc if desc else (prev.get("description", "") if prev else ""),
            "values": snap,
        }
        if prev:
            if not (body.name or "").strip():
                entry["label"] = prev.get("label", pid)
            if not desc:
                entry["description"] = prev.get("description", "")
        norm[pid] = entry
        _save_model_profiles(layer8_dir, _serialize_profiles_to_disk(norm))
        return {"profiles": norm}

    @router.post("/api/model/profiles/sync_from_config")
    def sync_profile_from_config(body: ApplyModelProfileBody) -> dict[str, Any]:
        """Merge current ui_settings webcam (camera + model keys) into profile.values."""
        pid = body.id.strip()
        if not pid:
            raise HTTPException(400, "id is required")
        s = load(layer8_dir)
        w = s.get("webcam") or {}
        snap = _extract_profile_values(w)
        norm = _get_model_profiles_normalized(layer8_dir)
        prev = norm.get(pid)
        if prev is None:
            norm[pid] = {"label": pid, "description": "", "values": dict(snap)}
        else:
            merged_vals = {**(prev.get("values") or {}), **snap}
            norm[pid] = {**prev, "values": merged_vals}
        _save_model_profiles(layer8_dir, _serialize_profiles_to_disk(norm))
        return {"profiles": norm}

    @router.get("/api/layer8/module_map")
    def layer8_module_map() -> dict[str, str]:
        """Which backend modules own each tab (for operators / integration)."""
        return {
            "thermal_tab": "layer8_ui.thermal_runner",
            "webcam_tab": "layer8_ui.webcam_runner",
            "model_tab": (
                "Live webcam infer: layer8_ui.webcam_runner → weapon_ai.webcam_layer8_runner "
                "→ weapon_ai.infer_thermal_objects (layer4_inference/weapon_ai/infer_thermal_objects.py). "
                "layer8_ui.inference_overlay is a stub for optional server-side overlays."
            ),
            "mmwave_tab": "layer8_ui.sensor_runner (mmWave CLI)",
        }

    @router.get("/api/command/{sensor}")
    def preview_command(sensor: SensorName) -> dict[str, Any]:
        if sensor not in ("thermal", "webcam", "mmwave"):
            raise HTTPException(400, "invalid sensor")
        s = load(layer8_dir)
        cmd = sensor_runner.build_command(sensor, s, layer8_dir)
        run_cwd = str(sensor_runner.command_cwd(sensor, s, layer8_dir))
        return {
            "command": cmd,
            "cwd": run_cwd,
            "software_root": str(sensor_runner.resolved_software_root(s)),
        }

    @router.get("/api/preview/video/{sensor}")
    def preview_video(sensor: Literal["thermal", "webcam", "mmwave"]) -> FileResponse:
        s = load(layer8_dir)
        key = "video"
        sub = (s.get(sensor) or {}).get(key) or ""
        path = resolved_artifact_path(s, relative_to_software=str(sub), layer8_dir=layer8_dir)
        if path is None or not path.is_file():
            raise HTTPException(
                404,
                "Video file not found. Run capture first, or fix the video path in settings "
                "(must be under software/ or layer8_ui/).",
            )
        return FileResponse(path, media_type="video/mp4", filename=path.name)

    @router.get("/api/preview/live/{sensor}")
    async def preview_live(sensor: SensorName) -> StreamingResponse:
        s = load(layer8_dir)
        rel = (s.get(sensor) or {}).get("live_frame") or ""
        path = resolved_artifact_path(s, relative_to_software=str(rel), layer8_dir=layer8_dir)
        if path is None:
            raise HTTPException(404, "live frame path not configured")

        label = {"thermal": "Thermal", "webcam": "Webcam", "mmwave": "mmWave"}.get(sensor, sensor)
        missing = mjpeg_placeholder_jpeg(
            f"{label}: no live JPEG yet",
            f"Expected file: {path.name}",
            "Start the sensor runner or fix live_frame in settings.",
        )

        async def mjpeg_stream():
            boundary = "frame"
            while True:
                jpg: bytes | None = None
                if path.is_file():
                    try:
                        raw = path.read_bytes()
                        if raw:
                            jpg = raw
                    except OSError:
                        jpg = None
                if not jpg:
                    jpg = missing
                chunk = (
                    f"--{boundary}\r\n"
                    "Content-Type: image/jpeg\r\n"
                    f"Content-Length: {len(jpg)}\r\n\r\n"
                ).encode("utf-8") + jpg + b"\r\n"
                yield chunk
                await asyncio.sleep(0.2)

        return StreamingResponse(
            mjpeg_stream(),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers=mjpeg_headers(),
        )

    @router.get("/api/preview/live_direct/thermal")
    async def preview_live_direct_thermal() -> StreamingResponse:
        st = sensor_runner.status("thermal", layer8_dir)
        s = load(layer8_dir)

        if bool(st.get("running")):
            rel = (s.get("thermal") or {}).get("live_frame") or ""
            rpath = resolved_artifact_path(s, relative_to_software=str(rel), layer8_dir=layer8_dir)
            runner_missing = mjpeg_placeholder_jpeg(
                "Thermal runner is ON (subprocess holds the camera).",
                "Showing JPEG from thermal.live_frame if the runner is writing it.",
                (rpath.name if rpath else "configure thermal.live_frame"),
            )

            async def mjpeg_runner_file():
                boundary = "frame"
                while True:
                    jpg: bytes | None = None
                    if rpath is not None and rpath.is_file():
                        try:
                            raw = rpath.read_bytes()
                            if raw:
                                jpg = raw
                        except OSError:
                            jpg = None
                    if not jpg:
                        jpg = runner_missing
                    chunk = (
                        f"--{boundary}\r\n"
                        "Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(jpg)}\r\n\r\n"
                    ).encode("utf-8") + jpg + b"\r\n"
                    yield chunk
                    await asyncio.sleep(0.2)

            return StreamingResponse(
                mjpeg_runner_file(),
                media_type="multipart/x-mixed-replace; boundary=frame",
                headers=mjpeg_headers(),
            )

        async def mjpeg_stream():
            boundary = "frame"
            thermal_stream.add_client(s)
            try:
                while True:
                    payload = thermal_stream.latest_jpg() or THERMAL_JPEG_WAITING
                    chunk = (
                        f"--{boundary}\r\n"
                        "Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(payload)}\r\n\r\n"
                    ).encode("utf-8") + payload + b"\r\n"
                    yield chunk
                    await asyncio.sleep(0.03)
            finally:
                thermal_stream.remove_client()

        return StreamingResponse(
            mjpeg_stream(),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers=mjpeg_headers(),
        )

    @router.get("/api/preview/live_direct/webcam")
    async def preview_live_direct_webcam() -> StreamingResponse:
        st = sensor_runner.status("webcam", layer8_dir)
        s = load(layer8_dir)

        if bool(st.get("running")):
            rel = (s.get("webcam") or {}).get("live_frame") or ""
            rpath = resolved_artifact_path(s, relative_to_software=str(rel), layer8_dir=layer8_dir)
            runner_missing = mjpeg_placeholder_jpeg(
                "Webcam runner is ON (subprocess holds the camera).",
                "Showing JPEG from webcam.live_frame if the runner is writing it.",
                (rpath.name if rpath else "configure webcam.live_frame"),
            )

            async def mjpeg_runner_file():
                boundary = "frame"
                while True:
                    jpg: bytes | None = None
                    if rpath is not None and rpath.is_file():
                        try:
                            raw = rpath.read_bytes()
                            if raw:
                                jpg = raw
                        except OSError:
                            jpg = None
                    if not jpg:
                        jpg = runner_missing
                    chunk = (
                        f"--{boundary}\r\n"
                        "Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(jpg)}\r\n\r\n"
                    ).encode("utf-8") + jpg + b"\r\n"
                    yield chunk
                    await asyncio.sleep(0.2)

            return StreamingResponse(
                mjpeg_runner_file(),
                media_type="multipart/x-mixed-replace; boundary=frame",
                headers=mjpeg_headers(),
            )

        async def mjpeg_stream():
            boundary = "frame"
            webcam_stream.add_client(s)
            try:
                while True:
                    payload = webcam_stream.latest_jpg() or WEBCAM_JPEG_WAITING
                    chunk = (
                        f"--{boundary}\r\n"
                        "Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(payload)}\r\n\r\n"
                    ).encode("utf-8") + payload + b"\r\n"
                    yield chunk
                    await asyncio.sleep(0.03)
            finally:
                webcam_stream.remove_client()

        return StreamingResponse(
            mjpeg_stream(),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers=mjpeg_headers(),
        )

    @router.websocket("/ws/thermal")
    async def websocket_thermal(websocket: WebSocket) -> None:
        await websocket.accept()
        held = False
        last_sent: bytes | None = None
        try:
            while True:
                s = load(layer8_dir)
                runner_on = bool(sensor_runner.status("thermal", layer8_dir).get("running"))
                if runner_on:
                    if held:
                        thermal_stream.remove_client()
                        held = False
                    rel = (s.get("thermal") or {}).get("live_frame") or ""
                    rpath = resolved_artifact_path(s, relative_to_software=str(rel), layer8_dir=layer8_dir)
                    jpg: bytes | None = None
                    if rpath is not None and rpath.is_file():
                        try:
                            raw = await asyncio.to_thread(rpath.read_bytes)
                            if raw:
                                jpg = raw
                        except OSError:
                            jpg = None
                    if not jpg:
                        jpg = mjpeg_placeholder_jpeg(
                            "Thermal runner is ON (subprocess holds the camera).",
                            "Showing JPEG from thermal.live_frame if the runner is writing it.",
                            (rpath.name if rpath else "configure thermal.live_frame"),
                        )
                    payload = jpg
                else:
                    if not held:
                        thermal_stream.add_client(s)
                        held = True
                    else:
                        thermal_stream.sync_settings(s)
                    payload = thermal_stream.latest_jpg() or THERMAL_JPEG_WAITING
                if payload != last_sent:
                    last_sent = payload
                    await websocket.send_bytes(payload)
                await asyncio.sleep(0.04)
        except (WebSocketDisconnect, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            if held:
                thermal_stream.remove_client()

    @router.websocket("/ws/webcam")
    async def websocket_webcam(websocket: WebSocket) -> None:
        """Binary JPEG stream; fan-out from one shared V4L2 reader (parallel with ``/ws/thermal``)."""
        await websocket.accept()
        held = False
        last_sent: bytes | None = None
        try:
            while True:
                s = load(layer8_dir)
                runner_on = bool(sensor_runner.status("webcam", layer8_dir).get("running"))
                if runner_on:
                    if held:
                        webcam_stream.remove_client()
                        held = False
                    rel = (s.get("webcam") or {}).get("live_frame") or ""
                    rpath = resolved_artifact_path(s, relative_to_software=str(rel), layer8_dir=layer8_dir)
                    jpg: bytes | None = None
                    if rpath is not None and rpath.is_file():
                        try:
                            raw = await asyncio.to_thread(rpath.read_bytes)
                            if raw:
                                jpg = raw
                        except OSError:
                            jpg = None
                    if not jpg:
                        jpg = mjpeg_placeholder_jpeg(
                            "Webcam runner is ON (subprocess holds the camera).",
                            "Showing JPEG from webcam.live_frame if the runner is writing it.",
                            (rpath.name if rpath else "configure webcam.live_frame"),
                        )
                    payload = jpg
                else:
                    if not held:
                        webcam_stream.add_client(s)
                        held = True
                    else:
                        webcam_stream.sync_settings(s)
                    payload = webcam_stream.latest_jpg() or WEBCAM_JPEG_WAITING
                if payload != last_sent:
                    last_sent = payload
                    await websocket.send_bytes(payload)
                await asyncio.sleep(0.04)
        except (WebSocketDisconnect, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            if held:
                webcam_stream.remove_client()

    @router.websocket("/ws/events")
    async def websocket_events(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            await websocket.send_json({"event_type": "status_update", "payload": _status_payload()})
            while True:
                status_payload = _status_payload()
                visual_payload = _visual_payload()
                await websocket.send_json({"event_type": "status_update", "payload": status_payload})
                await websocket.send_json({"event_type": "visual_update", "payload": visual_payload})
                if bool(status_payload.get("health", {}).get("has_fault")):
                    await websocket.send_json(
                        {
                            "event_type": "sensor_fault",
                            "payload": {
                                "timestamp_utc": _iso_now(),
                                "message": "No sensors are currently running.",
                            },
                        }
                    )
                await asyncio.sleep(1.0)
        except (WebSocketDisconnect, ConnectionResetError, BrokenPipeError):
            pass

    @router.get("/embed/thermal")
    def embed_thermal_page() -> FileResponse:
        """Minimal full-page thermal viewer for a second screen or another operator."""
        p = layer8_dir / "static" / "embed_thermal.html"
        if not p.is_file():
            raise HTTPException(404, "static/embed_thermal.html missing")
        return FileResponse(p, media_type="text/html")

    @router.get("/embed/webcam")
    def embed_webcam_page() -> FileResponse:
        """Minimal full-page webcam viewer; use alongside ``/embed/thermal`` on another device."""
        p = layer8_dir / "static" / "embed_webcam.html"
        if not p.is_file():
            raise HTTPException(404, "static/embed_webcam.html missing")
        return FileResponse(p, media_type="text/html")

    @router.get("/api/preview/output/mmwave")
    def preview_mmwave_output() -> FileResponse:
        s = load(layer8_dir)
        sub = (s.get("mmwave") or {}).get("output") or ""
        path = resolved_artifact_path(s, relative_to_software=str(sub), layer8_dir=layer8_dir)
        if path is None or not path.is_file():
            raise HTTPException(
                404,
                "Output JSON not found. Run mmWave capture or set output path in settings.",
            )
        return FileResponse(path, media_type="application/json", filename=path.name)

    @router.get("/api/dashboard/metrics")
    def dashboard_metrics() -> dict[str, Any]:
        return _read_metrics()

    @router.get("/api/status")
    def all_status() -> dict[str, Any]:
        return _status_payload()

    @router.get("/api/health")
    def get_health() -> dict[str, Any]:
        return _health_payload()

    @router.get("/api/alerts/recent")
    def get_recent_alerts(limit: int = 50) -> dict[str, Any]:
        return _alerts_payload(limit=limit)

    @router.get("/api/visual/latest")
    def get_visual_latest() -> dict[str, Any]:
        return _visual_payload()

    @router.get("/api/visual/rgb")
    def get_visual_rgb() -> dict[str, Any]:
        visual = _visual_payload()
        return {
            "timestamp_ms": visual.get("timestamp_ms"),
            "source_mode": visual.get("source_mode"),
            "rgb_jpeg_b64": visual.get("rgb_jpeg_b64"),
            "meta": visual.get("meta", {}),
        }

    @router.get("/api/visual/thermal")
    def get_visual_thermal() -> dict[str, Any]:
        visual = _visual_payload()
        return {
            "timestamp_ms": visual.get("timestamp_ms"),
            "source_mode": visual.get("source_mode"),
            "thermal_jpeg_b64": visual.get("thermal_jpeg_b64"),
            "meta": visual.get("meta", {}),
        }

    @router.get("/api/visual/point-cloud")
    def get_visual_point_cloud() -> dict[str, Any]:
        visual = _visual_payload()
        return {
            "timestamp_ms": visual.get("timestamp_ms"),
            "source_mode": visual.get("source_mode"),
            "point_cloud": visual.get("point_cloud", []),
            "meta": visual.get("meta", {}),
        }

    @router.get("/api/visual/presence")
    def get_visual_presence() -> dict[str, Any]:
        visual = _visual_payload()
        return {
            "timestamp_ms": visual.get("timestamp_ms"),
            "source_mode": visual.get("source_mode"),
            "presence": visual.get("presence"),
            "meta": visual.get("meta", {}),
        }

    @router.get("/api/ui/preferences")
    def get_ui_preferences() -> dict[str, Any]:
        return _load_ui_prefs(layer8_dir)

    @router.post("/api/ui/preferences")
    def set_ui_preferences(payload: UiPreferencesPayload) -> dict[str, Any]:
        return _save_ui_prefs(layer8_dir, payload.model_dump())

    @router.get("/api/status/stream")
    async def stream_status() -> StreamingResponse:
        async def event_stream():
            while True:
                payload = {name: sensor_runner.status(name, layer8_dir) for name in ("thermal", "webcam", "mmwave")}
                yield f"event: status\ndata: {json.dumps(payload)}\n\n"
                await asyncio.sleep(1.0)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @router.get("/api/status/{sensor}")
    def one_status(sensor: SensorName) -> dict[str, Any]:
        return sensor_runner.status(sensor, layer8_dir)

    @router.post("/api/run/{sensor}")
    def run_sensor(sensor: SensorName) -> dict[str, Any]:
        s = load(layer8_dir)
        if sensor == "thermal":
            thermal_stream.pause_for_thermal_subprocess()
        if sensor == "webcam":
            webcam_stream.pause_for_webcam_subprocess()
        try:
            result = sensor_runner.start(sensor, s, layer8_dir)
        finally:
            if sensor == "thermal":
                thermal_stream.resume_after_thermal_subprocess_attempt()
            if sensor == "webcam":
                webcam_stream.resume_after_webcam_subprocess_attempt()
        if not result.get("ok"):
            return JSONResponse(result, status_code=409)
        return result

    @router.post("/api/stop/{sensor}")
    def stop_sensor(sensor: SensorName) -> dict[str, Any]:
        return sensor_runner.stop(sensor, layer8_dir)

    @router.post("/api/restart/{sensor}")
    def restart_sensor(sensor: SensorName) -> dict[str, Any]:
        s = load(layer8_dir)
        if sensor == "thermal":
            thermal_stream.pause_for_thermal_subprocess()
        if sensor == "webcam":
            webcam_stream.pause_for_webcam_subprocess()
        try:
            result = sensor_runner.restart(sensor, s, layer8_dir)
        finally:
            if sensor == "thermal":
                thermal_stream.resume_after_thermal_subprocess_attempt()
            if sensor == "webcam":
                webcam_stream.resume_after_webcam_subprocess_attempt()
        if not result.get("ok"):
            return JSONResponse(result, status_code=409)
        return result

    @router.post("/api/run_all")
    def run_all_sensors() -> dict[str, Any]:
        s = load(layer8_dir)
        results: dict[str, Any] = {}
        started: list[SensorName] = []
        thermal_stream.pause_for_thermal_subprocess()
        try:
            for sensor in ("thermal", "webcam", "mmwave"):
                if sensor == "webcam":
                    webcam_stream.pause_for_webcam_subprocess()
                try:
                    res = sensor_runner.start(sensor, s, layer8_dir)
                finally:
                    if sensor == "webcam":
                        webcam_stream.resume_after_webcam_subprocess_attempt()
                results[sensor] = res
                if res.get("ok"):
                    started.append(sensor)
                    continue
                for started_sensor in started:
                    sensor_runner.stop(started_sensor, layer8_dir)
                return JSONResponse(
                    {
                        "ok": False,
                        "error": f"Failed to start {sensor}",
                        "results": results,
                    },
                    status_code=409,
                )
            return {"ok": True, "results": results}
        finally:
            thermal_stream.resume_after_thermal_subprocess_attempt()

    @router.post("/api/stop_all")
    def stop_all_sensors() -> dict[str, Any]:
        return {
            "ok": True,
            "results": {
                sensor: sensor_runner.stop(sensor, layer8_dir) for sensor in ("thermal", "webcam", "mmwave")
            },
        }

    @router.post("/api/restart_all")
    def restart_all_sensors() -> dict[str, Any]:
        sensor_runner.stop("thermal", layer8_dir)
        sensor_runner.stop("webcam", layer8_dir)
        sensor_runner.stop("mmwave", layer8_dir)
        return run_all_sensors()

    @router.post("/api/control/reconfig")
    def control_reconfig(body: CompatReconfigRequest) -> dict[str, Any]:
        text = (body.config_text or "").lower()
        if "sensorstop" in text and "sensorstart" in text:
            result = restart_all_sensors()
            success, details = _normalize_route_result(result)
            return {
                "radar_id": body.radar_id,
                "action": "apply_config",
                "success": success,
                "reason": None if success else "restart_all_failed",
                "details": details,
            }
        if "sensorstop" in text:
            result = stop_all_sensors()
            success, details = _normalize_route_result(result)
            return {
                "radar_id": body.radar_id,
                "action": "apply_config",
                "success": success,
                "reason": None if success else "stop_all_failed",
                "details": details,
            }

        result = run_all_sensors()
        success, details = _normalize_route_result(result)
        return {
            "radar_id": body.radar_id,
            "action": "apply_config",
            "success": success,
            "reason": None if success else "run_all_failed",
            "details": details,
        }

    @router.post("/api/control/reset-soft")
    def control_reset_soft(body: CompatResetSoftRequest) -> dict[str, Any]:
        result = restart_all_sensors()
        success, details = _normalize_route_result(result)
        return {
            "radar_id": body.radar_id,
            "action": "reset_soft",
            "success": success,
            "reason": None if success else "restart_all_failed",
            "details": details,
        }

    return router


def index_handler(static_dir: Path) -> FileResponse:
    index_path = Path(static_dir) / "index.html"
    if not index_path.is_file():
        raise HTTPException(404, "static/index.html missing")
    return FileResponse(index_path)
