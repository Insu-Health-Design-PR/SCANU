"""HTTP + WebSocket routes for the Layer 8 static dashboard (no business rules in ``app``)."""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from layer8_ui import sensor_runner, thermal_runner, webcam_runner
from layer8_ui.artifact_paths import resolved_artifact_path
from layer8_ui.preview_media import (
    THERMAL_JPEG_WAITING,
    WEBCAM_JPEG_WAITING,
    mjpeg_headers,
    mjpeg_placeholder_jpeg,
)
from layer8_ui.settings_store import DEFAULT_SETTINGS, load, reset_webcam_weapon_defaults, save

SensorName = Literal["thermal", "webcam", "mmwave"]


class SettingsBody(BaseModel):
    settings: dict[str, Any]


def build_router(layer8_dir: Path) -> APIRouter:
    layer8_dir = Path(layer8_dir).resolve()
    thermal_stream = thermal_runner.get_thermal_shared_stream(layer8_dir)
    webcam_stream = webcam_runner.get_webcam_shared_stream(layer8_dir)
    router = APIRouter()

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
        return {
            "unsafe_pct": None,
            "gun_detected": None,
            "persons_with_gun": None,
            "prediction": None,
            "mmwave_torso_score": None,
            "note": "Wire Layer 5 fusion or weapon-infer sidecar JSON to populate these fields.",
        }

    @router.get("/api/status")
    def all_status() -> dict[str, Any]:
        return {name: sensor_runner.status(name, layer8_dir) for name in ("thermal", "webcam", "mmwave")}

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

    return router


def index_handler(static_dir: Path) -> FileResponse:
    index_path = Path(static_dir) / "index.html"
    if not index_path.is_file():
        raise HTTPException(404, "static/index.html missing")
    return FileResponse(index_path)
