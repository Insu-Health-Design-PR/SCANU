"""Shared helper closures used across route modules."""

from __future__ import annotations

import base64
import json
import time
import uuid
from typing import Any, Literal

from layer1_sensor_hub.mmwave import (
    CameraProjectionConfig,
    MovementTrailTracker,
    load_normalized_mmwave_frames,
    normalize_mmwave_frame,
    project_frame_to_camera,
    render_top_down_jpeg,
)
from layer8_ui import sensor_runner, thermal_runner, webcam_runner
from layer8_ui.artifact_paths import (
    resolved_artifact_path,
    software_root_from_settings,
)
from layer8_ui.routes.context import RouterContext
from layer8_ui.settings_store import load


def iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sensor_statuses(ctx: RouterContext) -> dict[str, dict[str, Any]]:
    return {
        name: sensor_runner.status(name, ctx.layer8_dir)
        for name in ("thermal", "webcam", "mmwave")
    }


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def normalize_alert_level(level: str) -> str:
    ll = str(level).strip().lower()
    if ll in {"fault", "error"}:
        return "fault"
    if ll in {"warning", "warn", "alert"}:
        return "warning"
    return "info"


def read_metrics(ctx: RouterContext) -> dict[str, Any]:
    s = load(ctx.layer8_dir)
    rel = (
        (s.get("webcam") or {}).get("metrics_json")
        or "layer8_ui/artifacts/live_threat_metrics.json"
    )
    path = resolved_artifact_path(
        s, relative_to_software=str(rel), layer8_dir=ctx.layer8_dir
    )
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


def read_live_jpeg_b64(
    ctx: RouterContext, sensor: Literal["thermal", "webcam"]
) -> str | None:
    s = load(ctx.layer8_dir)
    runner_on = bool(
        sensor_runner.status(sensor, ctx.layer8_dir).get("running")
    )
    rel = (s.get(sensor) or {}).get("live_frame") or ""
    path = resolved_artifact_path(
        s, relative_to_software=str(rel), layer8_dir=ctx.layer8_dir
    )

    raw: bytes | None = None
    if runner_on and path is not None and path.is_file():
        try:
            raw = path.read_bytes()
        except OSError:
            raw = None
    else:
        if sensor == "thermal":
            raw = ctx.thermal_stream.latest_jpg()
        else:
            raw = ctx.webcam_stream.latest_jpg()
        if not raw and path is not None and path.is_file():
            try:
                raw = path.read_bytes()
            except OSError:
                raw = None
    if not raw:
        return None
    return base64.b64encode(raw).decode("ascii")


def read_point_cloud(ctx: RouterContext) -> list[dict[str, float]]:
    frame = read_last_mmwave_frame(ctx)
    if frame is None:
        return []
    points = (
        frame.get("objects") if isinstance(frame, dict) else []
    )
    if not isinstance(points, list):
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


def mmwave_output_path(ctx: RouterContext) -> Path | None:
    from pathlib import Path

    s = load(ctx.layer8_dir)
    rel = (
        (s.get("mmwave") or {}).get("output")
        or "layer8_ui/artifacts/mmwave_frames.json"
    )
    return resolved_artifact_path(
        s, relative_to_software=str(rel), layer8_dir=ctx.layer8_dir
    )


def read_mmwave_frames_normalized(
    ctx: RouterContext, limit: int = 250
) -> list[dict[str, Any]]:
    path = mmwave_output_path(ctx)
    if path is None or not path.is_file():
        return []
    frames = load_normalized_mmwave_frames(path)
    if limit > 0:
        frames = frames[-limit:]
    if frames:
        ctx.mmwave_trail_tracker.update(frames[-1])
    return [frame.to_dict() for frame in frames]


def read_last_mmwave_frame(ctx: RouterContext) -> dict[str, Any] | None:
    frames = read_mmwave_frames_normalized(ctx, limit=1)
    if frames:
        return frames[-1]
    return None


def read_last_mmwave_raw_frame(ctx: RouterContext) -> dict[str, Any] | None:
    from pathlib import Path

    path = mmwave_output_path(ctx)
    if path is None or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, list) or not payload:
        return None
    return payload[-1] if isinstance(payload[-1], dict) else None


def mmwave_projection_config(ctx: RouterContext) -> CameraProjectionConfig:
    s = load(ctx.layer8_dir)
    m = s.get("mmwave") or {}
    return CameraProjectionConfig.from_mapping(
        {
            "width": m.get("projection_width", 1280),
            "height": m.get("projection_height", 720),
            "x_scale_px_per_m": m.get("projection_x_scale_px_per_m", 120.0),
            "y_scale_px_per_m": m.get("projection_y_scale_px_per_m", 90.0),
            "x_offset_px": m.get("projection_x_offset_px", 0.0),
            "y_offset_px": m.get("projection_y_offset_px", 0.0),
            "rotation_deg": m.get("projection_rotation_deg", 0.0),
            "max_range_m": m.get("projection_max_range_m", 12.0),
        }
    )


def device_grid_payload(ctx: RouterContext) -> dict[str, Any]:
    statuses = sensor_statuses(ctx)
    metrics = read_metrics(ctx)
    mmwave_frames = read_mmwave_frames_normalized(ctx, limit=1)
    mmwave_last = mmwave_frames[-1] if mmwave_frames else None
    now_ms = time.time() * 1000.0
    s = load(ctx.layer8_dir)
    mode = str((s.get("mmwave") or {}).get("mode") or "central")
    has_fault = all(
        not bool((statuses.get(sensor) or {}).get("running"))
        for sensor in ("webcam", "thermal", "mmwave")
    )
    recovery_state = (
        "degraded"
        if has_fault
        else ("fallback" if mode == "fallback" else "restored")
    )

    devices = []
    for sensor in ("webcam", "thermal", "mmwave"):
        st = statuses.get(sensor) or {}
        running = bool(st.get("running"))
        health = "online" if running else "offline"
        detail = "idle"
        if sensor == "webcam":
            if bool(metrics.get("gun_detected")):
                health = "warning"
                detail = "weapon alert"
            else:
                detail = (
                    f"persons={to_int(metrics.get('persons_total'), 0)}"
                )
        elif sensor == "mmwave":
            count = int((mmwave_last or {}).get("object_count") or 0)
            detail = f"objects={count}"
            if count > 0 and not running:
                health = "warning"
        devices.append(
            {
                "id": sensor,
                "label": "mmWave" if sensor == "mmwave" else sensor.title(),
                "kind": "radar" if sensor == "mmwave" else "camera",
                "status": health,
                "running": running,
                "pid": st.get("pid") or 0,
                "detail": detail,
                "last_seen_ms": (
                    now_ms
                    if running or (sensor == "mmwave" and mmwave_last)
                    else None
                ),
            }
        )
    return {
        "timestamp_ms": int(now_ms),
        "mode": mode,
        "recovery_state": recovery_state,
        "devices": devices,
    }


def status_payload(ctx: RouterContext) -> dict[str, Any]:
    statuses = sensor_statuses(ctx)
    online_count = sum(
        1 for s in statuses.values() if bool(s.get("running"))
    )
    metrics = read_metrics(ctx)
    point_cloud = read_point_cloud(ctx)
    mmwave_frame = read_last_mmwave_frame(ctx)
    confidence = 0.0
    if isinstance(metrics.get("unsafe_score"), (int, float)):
        confidence = float(metrics["unsafe_score"])
    elif isinstance(metrics.get("unsafe_pct"), (int, float)):
        confidence = max(
            0.0, min(1.0, float(metrics["unsafe_pct"]) / 100.0)
        )
    has_fault = online_count == 0
    state = "SCANNING" if online_count > 0 else "IDLE"
    fused_score = confidence
    active_radars: list[str] = (
        ["radar_main"]
        if bool(statuses.get("mmwave", {}).get("running"))
        else []
    )

    l6 = layer6_tick(
        ctx,
        statuses=statuses,
        metrics=metrics,
        point_cloud=point_cloud,
        mmwave_frame=mmwave_frame,
    )
    snapshot = l6.get("snapshot")
    if snapshot is not None:
        snap_state = getattr(snapshot, "state", state)
        state = str(
            snap_state.value
            if hasattr(snap_state, "value")
            else snap_state
        )
        fused_score = to_float(
            getattr(snapshot, "fused_score", fused_score), fused_score
        )
        confidence = to_float(
            getattr(snapshot, "confidence", confidence), confidence
        )
        snap_health = getattr(snapshot, "health", {}) or {}
        has_fault = bool(
            snap_health.get("has_fault", has_fault)
        )
        online_count = to_int(
            snap_health.get("sensor_online_count", online_count),
            online_count,
        )
        act = getattr(snapshot, "active_radars", tuple()) or tuple()
        active_radars = (
            [str(x) for x in act] if act else active_radars
        )

    return {
        "state": state,
        "fused_score": fused_score,
        "confidence": confidence,
        "health": {
            "has_fault": has_fault,
            "sensor_online_count": online_count,
        },
        "active_radars": active_radars,
    }


def health_payload(ctx: RouterContext) -> dict[str, Any]:
    status = status_payload(ctx)
    online_count = int(status["health"]["sensor_online_count"])
    has_fault = bool(status["health"]["has_fault"])
    return {
        "healthy": online_count > 0 and not has_fault,
        "has_fault": has_fault,
        "sensor_online_count": online_count,
    }


def visual_payload(ctx: RouterContext) -> dict[str, Any]:
    metrics = read_metrics(ctx)
    statuses = sensor_statuses(ctx)
    online_count = sum(
        1 for s in statuses.values() if bool(s.get("running"))
    )
    detected = bool(metrics.get("gun_detected")) or (
        int(metrics.get("persons_total") or 0) > 0
    )
    confidence = 0.0
    if isinstance(metrics.get("unsafe_score"), (int, float)):
        confidence = float(metrics["unsafe_score"])
    elif isinstance(metrics.get("unsafe_pct"), (int, float)):
        confidence = max(
            0.0, min(1.0, float(metrics["unsafe_pct"]) / 100.0)
        )
    return {
        "timestamp_ms": int(time.time() * 1000),
        "source_mode": "live" if online_count > 0 else "simulate",
        "rgb_jpeg_b64": read_live_jpeg_b64(ctx, "webcam"),
        "thermal_jpeg_b64": read_live_jpeg_b64(ctx, "thermal"),
        "point_cloud": read_point_cloud(ctx),
        "presence": {
            "detected": detected,
            "confidence": confidence,
        },
        "meta": {
            "ready": online_count > 0,
            "rgb_enabled": bool(
                statuses.get("webcam", {}).get("running")
            ),
            "thermal_enabled": bool(
                statuses.get("thermal", {}).get("running")
            ),
            "point_cloud_enabled": bool(
                statuses.get("mmwave", {}).get("running")
            ),
            "presence_enabled": True,
        },
    }


def layer6_tick(
    ctx: RouterContext,
    *,
    statuses: dict[str, dict[str, Any]] | None = None,
    metrics: dict[str, Any] | None = None,
    point_cloud: list[dict[str, float]] | None = None,
    mmwave_frame: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if ctx.layer6_orchestrator is None:
        return {}
    try:
        from layer6_state_machine.models import SystemHealth
    except Exception:
        return {}

    now_ms = float(time.time() * 1000.0)
    if not force and (
        now_ms - float(ctx.layer6_cache.get("ts_ms") or 0.0)
    ) < 150.0:
        return dict(ctx.layer6_cache)

    if statuses is None:
        statuses = sensor_statuses(ctx)
    if metrics is None:
        metrics = read_metrics(ctx)
    if point_cloud is None:
        point_cloud = read_point_cloud(ctx)
    if mmwave_frame is None:
        mmwave_frame = read_last_mmwave_frame(ctx)

    online_count = sum(
        1 for s in statuses.values() if bool(s.get("running"))
    )
    confidence = 0.0
    if isinstance(metrics.get("unsafe_score"), (int, float)):
        confidence = to_float(metrics.get("unsafe_score"), 0.0)
    elif isinstance(metrics.get("unsafe_pct"), (int, float)):
        confidence = max(
            0.0,
            min(
                1.0,
                to_float(metrics.get("unsafe_pct"), 0.0) / 100.0,
            ),
        )

    mmwave_payload: dict[str, Any] = {"points": point_cloud or []}
    if mmwave_frame is not None:
        wt = mmwave_frame.get("weapon_track")
        if wt is not None:
            mmwave_payload["weapon_track"] = wt
        for field in (
            "micro_doppler_bw",
            "doppler_centroid",
            "azimuth_static_peak",
            "rcs_proxy_mean",
        ):
            if field in mmwave_frame:
                mmwave_payload[field] = mmwave_frame[field]

    raw_inputs = {
        "frame_number": to_int(
            metrics.get("frame"), int(now_ms) % 1_000_000
        ),
        "timestamp_ms": now_ms,
        "radar_id": "radar_main",
        "mmwave_frame": mmwave_payload,
        "presence_frame": {
            "presence_raw": confidence,
            "motion_raw": confidence,
        },
        "thermal_presence": confidence,
        "fused_score": confidence,
        "gun_detected": bool(metrics.get("gun_detected")),
        "unsafe_score_l4": to_float(metrics.get("unsafe_score"), 0.0),
    }
    health = SystemHealth(
        has_fault=(online_count == 0),
        fault_code=(
            "no_sensors_online" if online_count == 0 else None
        ),
        fault_clear_requested=(online_count > 0),
        sensor_online_count=online_count,
    )
    try:
        event, snapshot, action_request = (
            ctx.layer6_orchestrator.tick(
                raw_inputs, health=health, now_ms=now_ms
            )
        )
        ctx.layer6_cache.update(
            {
                "ts_ms": now_ms,
                "event": event,
                "snapshot": snapshot,
                "action_request": action_request,
            }
        )
        return dict(ctx.layer6_cache)
    except Exception:
        return {}


def alerts_payload(
    ctx: RouterContext, limit: int = 50
) -> dict[str, Any]:
    status = status_payload(ctx)
    health = health_payload(ctx)
    metrics = read_metrics(ctx)
    statuses = sensor_statuses(ctx)
    point_cloud = read_point_cloud(ctx)
    mmwave_frame = read_last_mmwave_frame(ctx)
    l6 = layer6_tick(
        ctx,
        statuses=statuses,
        metrics=metrics,
        point_cloud=point_cloud,
        mmwave_frame=mmwave_frame,
        force=True,
    )
    event = l6.get("event")
    snapshot = l6.get("snapshot")
    action_request = l6.get("action_request")

    if ctx.layer7_bridge is not None and event is not None:
        try:
            if getattr(event, "previous_state", None) != getattr(
                event, "current_state", None
            ):
                payload = ctx.layer7_bridge.ingest(
                    event,
                    snapshot=snapshot,
                    action_request=action_request,
                )
                ctx.layer7_recent_alerts.appendleft(
                    {
                        "event_id": payload.event_id,
                        "level": normalize_alert_level(
                            str(payload.level.value)
                        ),
                        "timestamp_utc": payload.timestamp_utc,
                        "message": payload.message,
                        "state": payload.state,
                        "radar_id": payload.radar_id,
                        "scores": payload.scores,
                        "metadata": payload.metadata,
                    }
                )
        except Exception:
            pass

    alerts: list[dict[str, Any]] = list(ctx.layer7_recent_alerts)
    if health["has_fault"]:
        alerts.append(
            {
                "event_id": f"fault-{uuid.uuid4().hex[:8]}",
                "level": "fault",
                "timestamp_utc": iso_now(),
                "message": "No sensors are currently running.",
            }
        )
    if bool(metrics.get("gun_detected")):
        gun_alert = build_l7_gun_alert(ctx, metrics)
        if gun_alert is not None:
            alerts.append(gun_alert)
        else:
            alerts.append(
                {
                    "event_id": f"warn-{uuid.uuid4().hex[:8]}",
                    "level": "warning",
                    "timestamp_utc": iso_now(),
                    "message": "Gun-like object detected by webcam inference.",
                }
            )
    if isinstance(metrics.get("note"), str) and metrics["note"]:
        alerts.append(
            {
                "event_id": f"info-{uuid.uuid4().hex[:8]}",
                "level": "info",
                "timestamp_utc": iso_now(),
                "message": metrics["note"],
            }
        )
    if not alerts:
        alerts.append(
            {
                "event_id": f"ok-{uuid.uuid4().hex[:8]}",
                "level": "info",
                "timestamp_utc": iso_now(),
                "message": f"System state: {status['state']}",
            }
        )
    return {"alerts": alerts[: max(1, int(limit))]}


def build_l7_gun_alert(
    ctx: RouterContext, metrics: dict[str, Any]
) -> dict[str, Any] | None:
    if ctx.layer7_bridge is None:
        return None
    try:
        from layer6_state_machine.models import (
            StateEvent,
            SystemState,
        )

        gun_conf = float(
            metrics.get("unsafe_score")
            or metrics.get("gun_confidence")
            or 0.75
        )
        event = StateEvent(
            previous_state=SystemState.IDLE,
            current_state=SystemState.ANOMALY_DETECTED,
            reason="gun_detected_l4",
            frame_number=int(metrics.get("frame", 0)),
            timestamp_ms=float(time.time() * 1000.0),
            radar_id="camera_main",
            scores={
                "unsafe_score": gun_conf,
                "gun_detected": 1.0,
            },
        )
        payload = ctx.layer7_bridge.ingest(event)
        return {
            "event_id": payload.event_id,
            "level": str(payload.level.value),
            "timestamp_utc": payload.timestamp_utc,
            "message": payload.message,
            "state": payload.state,
            "radar_id": payload.radar_id,
            "scores": payload.scores,
            "metadata": payload.metadata,
        }
    except Exception:
        return None


def layers_summary_payload(ctx: RouterContext) -> dict[str, Any]:
    from pathlib import Path

    s = load(ctx.layer8_dir)
    sw = software_root_from_settings(s)
    statuses = sensor_statuses(ctx)
    metrics = read_metrics(ctx)
    point_cloud = read_point_cloud(ctx)
    mmwave_frame = read_last_mmwave_frame(ctx)
    l6 = layer6_tick(
        ctx,
        statuses=statuses,
        metrics=metrics,
        point_cloud=point_cloud,
        mmwave_frame=mmwave_frame,
    )
    snapshot = l6.get("snapshot")

    layer2_features = (
        sw / "layer2_signal_processing" / "layer2_features.json"
    )
    layer3_dataset = sw / "layer3_features" / "dataset.py"
    layer4_metrics_rel = (
        (s.get("webcam") or {}).get("metrics_json")
        or "layer8_ui/artifacts/live_threat_metrics.json"
    )
    layer4_metrics_path = resolved_artifact_path(
        s,
        relative_to_software=str(layer4_metrics_rel),
        layer8_dir=ctx.layer8_dir,
    )
    layer5_dir = sw / "layer5_fusion"
    layer5_impl = [
        p.name
        for p in layer5_dir.glob("*.py")
        if p.name != "__init__.py"
    ]

    state_value = ""
    fused_score = 0.0
    if snapshot is not None:
        snap_state = getattr(snapshot, "state", "")
        state_value = str(
            snap_state.value
            if hasattr(snap_state, "value")
            else snap_state
        )
        fused_score = to_float(
            getattr(snapshot, "fused_score", 0.0), 0.0
        )

    return {
        "timestamp_ms": int(time.time() * 1000),
        "layers": {
            "layer1": {
                "mmwave_running": bool(
                    statuses.get("mmwave", {}).get("running")
                ),
                "thermal_running": bool(
                    statuses.get("thermal", {}).get("running")
                ),
                "webcam_running": bool(
                    statuses.get("webcam", {}).get("running")
                ),
                "sensor_online_count": sum(
                    1
                    for s in statuses.values()
                    if bool(s.get("running"))
                ),
            },
            "layer2": {
                "features_file": str(layer2_features),
                "features_file_exists": layer2_features.is_file(),
            },
            "layer3": {
                "dataset_module": str(layer3_dataset),
                "dataset_module_exists": layer3_dataset.is_file(),
            },
            "layer4": {
                "metrics_path": (
                    str(layer4_metrics_path)
                    if layer4_metrics_path is not None
                    else ""
                ),
                "metrics_available": bool(
                    layer4_metrics_path
                    and layer4_metrics_path.is_file()
                ),
                "gun_detected": bool(metrics.get("gun_detected")),
                "persons_total": to_int(
                    metrics.get("persons_total"), 0
                ),
            },
            "layer5": {
                "module_dir": str(layer5_dir),
                "implementation_files": layer5_impl,
                "implemented": len(layer5_impl) > 0,
            },
            "layer6": {
                "integrated": ctx.layer6_orchestrator is not None,
                "state": state_value,
                "fused_score": fused_score,
            },
            "layer7": {
                "integrated": ctx.layer7_bridge is not None,
                "recent_alerts_count": len(
                    ctx.layer7_recent_alerts
                ),
            },
            "layer8": {
                "api_ready": True,
            },
        },
    }


def normalize_route_result(
    result: Any,
) -> tuple[bool, Any]:
    if hasattr(result, "body"):
        try:
            import json

            payload = json.loads(result.body.decode("utf-8"))
        except Exception:
            payload = {"ok": False, "error": "invalid_json_response"}
        return bool(payload.get("ok")), payload
    if isinstance(result, dict):
        return bool(result.get("ok")), result
    return False, {"ok": False, "error": "unexpected_result_type"}
