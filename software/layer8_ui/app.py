"""
Layer 8 sensor dashboard: run thermal, webcam (live weapon infer), and mmWave captures separately.

  uvicorn layer8_ui.app:app --reload --host 0.0.0.0 --port 8088

Or from repo `software/` directory:

  python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from layer8_ui import sensor_runner
from layer8_ui.settings_store import DEFAULT_SETTINGS, load, save
from layer8_ui.thermal_device import detect_working_thermal_device

_THERMAL_CAM_CFG_LEN = 9

LAYER8_DIR = Path(__file__).resolve().parent
ARTIFACTS = LAYER8_DIR / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="SCANU Layer 8 — sensor runners", version="0.1.0")
STATIC = LAYER8_DIR / "static"
if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


class SettingsBody(BaseModel):
    settings: dict[str, Any]


SensorName = Literal["thermal", "webcam", "mmwave"]


class _ThermalSharedStream:
    """Single thermal camera reader shared by all connected clients."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # camera-only tuple; see _cfg_from_settings
        self._cfg: tuple[Any, ...] | None = None
        self._cfg_dirty = False
        self._latest_jpg: bytes | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._clients = 0
        self._resolved_device: int | None = None
        self._next_detect_retry_ts = 0.0

    @staticmethod
    def _cfg_from_settings(settings: dict[str, Any]) -> tuple[Any, ...]:
        t = settings.get("thermal") or {}
        requested_device = int(t.get("thermal_device", 0))
        thermal_auto_detect = int(t.get("thermal_auto_detect", 1))
        thermal_detect_max_index = int(t.get("thermal_detect_max_index", 6))
        thermal_detect_retry_s = float(t.get("thermal_detect_retry_s", 12.0))
        thermal_width = int(t.get("thermal_width", 160))
        thermal_height = int(t.get("thermal_height", 120))
        thermal_fps = int(t.get("thermal_fps", 9))
        return (
            requested_device,
            thermal_width,
            thermal_height,
            thermal_fps,
            int(t.get("panel_w", 640)),
            int(t.get("panel_h", 480)),
            thermal_auto_detect,
            thermal_detect_max_index,
            thermal_detect_retry_s,
        )

    def add_client(self, settings: dict[str, Any]) -> None:
        new_cfg = self._cfg_from_settings(settings)
        with self._lock:
            self._clients += 1
            if self._cfg != new_cfg:
                self._cfg = new_cfg
                self._cfg_dirty = True
                self._resolved_device = None
                self._next_detect_retry_ts = 0.0
            if self._thread is None or not self._thread.is_alive():
                self._stop_event.clear()
                self._thread = threading.Thread(target=self._run, name="thermal-shared-stream", daemon=True)
                self._thread.start()

    def remove_client(self) -> None:
        with self._lock:
            self._clients = max(0, self._clients - 1)
            if self._clients == 0:
                self._stop_event.set()

    def latest_jpg(self) -> bytes | None:
        with self._lock:
            return self._latest_jpg

    def _run(self) -> None:
        cap: cv2.VideoCapture | None = None
        active_camera_cfg: tuple[Any, ...] | None = None
        next_open_retry_ts = 0.0
        try:
            while not self._stop_event.is_set():
                with self._lock:
                    clients = self._clients
                    cfg = self._cfg
                    cfg_dirty = self._cfg_dirty
                    if self._cfg_dirty:
                        self._cfg_dirty = False

                if clients <= 0 or cfg is None:
                    time.sleep(0.05)
                    continue

                settings_cam_cfg = cfg[:_THERMAL_CAM_CFG_LEN]
                if cap is None or cfg_dirty or settings_cam_cfg != active_camera_cfg:
                    now_ts = time.time()
                    if now_ts < next_open_retry_ts:
                        time.sleep(0.05)
                        continue
                    if cap is not None:
                        cap.release()
                        cap = None
                    preferred_device, width, height, fps, _, _, thermal_auto_detect, detect_max_index, detect_retry_s = (
                        settings_cam_cfg
                    )
                    device = self._resolved_device if self._resolved_device is not None else int(preferred_device)
                    cap = cv2.VideoCapture(int(device), cv2.CAP_V4L2)
                    if not cap.isOpened():
                        cap.release()
                        cap = None
                        if thermal_auto_detect:
                            fallback_device = None
                            if now_ts >= self._next_detect_retry_ts:
                                fallback_device = detect_working_thermal_device(
                                    preferred=int(preferred_device),
                                    width=int(width),
                                    height=int(height),
                                    fps=int(fps),
                                    search_max_index=int(detect_max_index),
                                )
                                # Retry window prevents probe spam while device is busy.
                                self._next_detect_retry_ts = now_ts + max(0.5, float(detect_retry_s))
                            if fallback_device is not None and fallback_device != int(device):
                                cap = cv2.VideoCapture(int(fallback_device), cv2.CAP_V4L2)
                                if cap.isOpened():
                                    device = int(fallback_device)
                                    self._resolved_device = int(fallback_device)
                                else:
                                    cap.release()
                                    cap = None
                            elif fallback_device is not None:
                                self._resolved_device = int(fallback_device)
                        if cap is not None and cap.isOpened():
                            active_camera_cfg = settings_cam_cfg
                            next_open_retry_ts = 0.0
                            cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
                            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("Y", "1", "6", " "))
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                            cap.set(cv2.CAP_PROP_FPS, fps)
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            continue
                        # Back off retries to avoid tight open-fail spam loops when device is unavailable.
                        next_open_retry_ts = now_ts + 1.5
                        time.sleep(0.1)
                        continue
                    cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("Y", "1", "6", " "))
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    cap.set(cv2.CAP_PROP_FPS, fps)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    self._resolved_device = int(device)
                    active_camera_cfg = settings_cam_cfg
                    next_open_retry_ts = 0.0

                ok, frame = cap.read()
                if not ok or frame is None:
                    time.sleep(0.03)
                    continue

                _, _, _, _, panel_w, panel_h, _thermal_auto_detect, _detect_max_index, _detect_retry_s = (
                    settings_cam_cfg
                )
                if frame.dtype == np.uint16:
                    f32 = frame.astype("float32")
                    mn = float(f32.min())
                    mx = float(f32.max())
                    if mx - mn > 1e-6:
                        gray = ((f32 - mn) / (mx - mn) * 255.0).astype("uint8")
                    else:
                        gray = cv2.convertScaleAbs(frame)
                elif len(frame.shape) == 2:
                    gray = frame
                elif len(frame.shape) == 3:
                    ch = int(frame.shape[2])
                    if ch == 1:
                        gray = frame[:, :, 0]
                    elif ch == 2:
                        # Some V4L modes deliver 2-channel packed data; BGR2GRAY is invalid.
                        gray = np.mean(frame, axis=2).astype(np.uint8)
                    elif ch == 3:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    elif ch == 4:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
                    else:
                        gray = np.mean(frame, axis=2).astype(np.uint8)
                else:
                    gray = frame

                heat = cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)
                heat = cv2.resize(heat, (panel_w, panel_h), interpolation=cv2.INTER_LINEAR)

                ok_enc, jpg = cv2.imencode(".jpg", heat, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ok_enc:
                    with self._lock:
                        self._latest_jpg = jpg.tobytes()
                time.sleep(0.01)
        finally:
            if cap is not None:
                cap.release()


_THERMAL_SHARED_STREAM = _ThermalSharedStream()


def _resolved_artifact_path_from_roots(
    *,
    software_root: str | Path,
    relative_to_software: str,
) -> Path | None:
    """Resolve a path; must stay under software_root or layer8_ui."""
    sw = Path(software_root).resolve()
    layer8 = LAYER8_DIR.resolve()
    rel = relative_to_software.strip()
    if not rel:
        return None
    p = Path(rel).expanduser()
    if p.is_absolute():
        ar = p.resolve()
        if ar.is_file():
            return ar
        return None
    cand = (sw / p).resolve()
    for base in (sw, layer8):
        try:
            cand.relative_to(base)
            return cand
        except ValueError:
            continue
    return None


def _resolved_artifact_path(
    settings: dict[str, Any],
    *,
    relative_to_software: str,
) -> Path | None:
    """Resolve a path from settings; must stay under software_root or layer8_ui."""
    return _resolved_artifact_path_from_roots(
        software_root=sensor_runner.resolved_software_root(settings),
        relative_to_software=relative_to_software,
    )


@app.get("/")
def index() -> FileResponse:
    index_path = STATIC / "index.html"
    if not index_path.is_file():
        raise HTTPException(404, "static/index.html missing")
    return FileResponse(index_path)


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    return load(LAYER8_DIR)


@app.put("/api/config")
def put_config(body: SettingsBody) -> dict[str, Any]:
    if not isinstance(body.settings, dict):
        raise HTTPException(400, "settings must be an object")
    save(LAYER8_DIR, body.settings)
    return load(LAYER8_DIR)


@app.post("/api/config/reset")
def reset_config() -> dict[str, Any]:
    """Reset all settings to defaults."""
    save(LAYER8_DIR, deepcopy(DEFAULT_SETTINGS))
    return load(LAYER8_DIR)


@app.post("/api/config/reset/{sensor}")
def reset_sensor_config(sensor: SensorName) -> dict[str, Any]:
    """Reset one sensor section to its default values."""
    current = load(LAYER8_DIR)
    current[sensor] = deepcopy(DEFAULT_SETTINGS[sensor])
    save(LAYER8_DIR, current)
    return load(LAYER8_DIR)


@app.get("/api/command/{sensor}")
def preview_command(sensor: SensorName) -> dict[str, Any]:
    if sensor not in ("thermal", "webcam", "mmwave"):
        raise HTTPException(400, "invalid sensor")
    s = load(LAYER8_DIR)
    cmd = sensor_runner.build_command(sensor, s, LAYER8_DIR)
    return {"command": cmd, "cwd": str(sensor_runner.resolved_software_root(s))}


@app.get("/api/preview/video/{sensor}")
def preview_video(sensor: Literal["thermal", "webcam", "mmwave"]) -> FileResponse:
    s = load(LAYER8_DIR)
    key = "video"
    sub = (s.get(sensor) or {}).get(key) or ""
    path = _resolved_artifact_path(s, relative_to_software=str(sub))
    if path is None or not path.is_file():
        raise HTTPException(
            404,
            "Video file not found. Run capture first, or fix the video path in settings "
            "(must be under software/ or layer8_ui/).",
        )
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@app.get("/api/preview/live/{sensor}")
async def preview_live(sensor: SensorName) -> StreamingResponse:
    s = load(LAYER8_DIR)
    rel = (s.get(sensor) or {}).get("live_frame") or ""
    path = _resolved_artifact_path(s, relative_to_software=str(rel))
    if path is None:
        raise HTTPException(404, "live frame path not configured")

    async def mjpeg_stream():
        boundary = "frame"
        while True:
            if path.is_file():
                try:
                    jpg = path.read_bytes()
                    chunk = (
                        f"--{boundary}\r\n"
                        "Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(jpg)}\r\n\r\n"
                    ).encode("utf-8") + jpg + b"\r\n"
                    yield chunk
                except OSError:
                    pass
            await asyncio.sleep(0.2)

    return StreamingResponse(
        mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/preview/live_direct/thermal")
async def preview_live_direct_thermal() -> StreamingResponse:
    """
    Real-time thermal MJPEG stream from one shared camera reader.
    Multiple clients can subscribe without contending for /dev/videoX.
    """
    # Prevent camera contention with the thermal runner process.
    st = sensor_runner.status("thermal", LAYER8_DIR)
    if bool(st.get("running")):
        raise HTTPException(
            409,
            "Direct thermal preview is disabled while thermal runner is active. "
            "Use /api/preview/live/thermal for runner output.",
        )

    s = load(LAYER8_DIR)

    async def mjpeg_stream():
        boundary = "frame"
        _THERMAL_SHARED_STREAM.add_client(s)
        try:
            while True:
                payload = _THERMAL_SHARED_STREAM.latest_jpg()
                if payload:
                    chunk = (
                        f"--{boundary}\r\n"
                        "Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(payload)}\r\n\r\n"
                    ).encode("utf-8") + payload + b"\r\n"
                    yield chunk
                await asyncio.sleep(0.03)
        finally:
            _THERMAL_SHARED_STREAM.remove_client()

    return StreamingResponse(
        mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/preview/output/mmwave")
def preview_mmwave_output() -> FileResponse:
    s = load(LAYER8_DIR)
    sub = (s.get("mmwave") or {}).get("output") or ""
    path = _resolved_artifact_path(s, relative_to_software=str(sub))
    if path is None or not path.is_file():
        raise HTTPException(
            404,
            "Output JSON not found. Run mmWave capture or set output path in settings.",
        )
    return FileResponse(path, media_type="application/json", filename=path.name)


@app.get("/api/dashboard/metrics")
def dashboard_metrics() -> dict[str, Any]:
    """
    Fusion / threat summary for the left rail. Placeholder until L5 writes a state file
    or log parsing is added; UI polls this for live updates.
    """
    return {
        "unsafe_pct": None,
        "gun_detected": None,
        "persons_with_gun": None,
        "prediction": None,
        "mmwave_torso_score": None,
        "note": "Wire Layer 5 fusion or weapon-infer sidecar JSON to populate these fields.",
    }


@app.get("/api/status")
def all_status() -> dict[str, Any]:
    out = {}
    for name in ("thermal", "webcam", "mmwave"):
        out[name] = sensor_runner.status(name, LAYER8_DIR)
    return out


@app.get("/api/status/stream")
async def stream_status() -> StreamingResponse:
    async def event_stream():
        while True:
            payload = {
                name: sensor_runner.status(name, LAYER8_DIR)
                for name in ("thermal", "webcam", "mmwave")
            }
            yield f"event: status\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/status/{sensor}")
def one_status(sensor: SensorName) -> dict[str, Any]:
    return sensor_runner.status(sensor, LAYER8_DIR)


@app.post("/api/run/{sensor}")
def run_sensor(sensor: SensorName) -> dict[str, Any]:
    s = load(LAYER8_DIR)
    result = sensor_runner.start(sensor, s, LAYER8_DIR)
    if not result.get("ok"):
        return JSONResponse(result, status_code=409)
    return result


@app.post("/api/stop/{sensor}")
def stop_sensor(sensor: SensorName) -> dict[str, Any]:
    return sensor_runner.stop(sensor, LAYER8_DIR)


@app.post("/api/restart/{sensor}")
def restart_sensor(sensor: SensorName) -> dict[str, Any]:
    s = load(LAYER8_DIR)
    result = sensor_runner.restart(sensor, s, LAYER8_DIR)
    if not result.get("ok"):
        return JSONResponse(result, status_code=409)
    return result


@app.post("/api/run_all")
def run_all_sensors() -> dict[str, Any]:
    s = load(LAYER8_DIR)
    results: dict[str, Any] = {}
    started: list[SensorName] = []
    for sensor in ("thermal", "webcam", "mmwave"):
        res = sensor_runner.start(sensor, s, LAYER8_DIR)
        results[sensor] = res
        if res.get("ok"):
            started.append(sensor)
            continue
        for started_sensor in started:
            sensor_runner.stop(started_sensor, LAYER8_DIR)
        return JSONResponse(
            {
                "ok": False,
                "error": f"Failed to start {sensor}",
                "results": results,
            },
            status_code=409,
        )
    return {"ok": True, "results": results}


@app.post("/api/stop_all")
def stop_all_sensors() -> dict[str, Any]:
    return {
        "ok": True,
        "results": {
            sensor: sensor_runner.stop(sensor, LAYER8_DIR)
            for sensor in ("thermal", "webcam", "mmwave")
        },
    }


@app.post("/api/restart_all")
def restart_all_sensors() -> dict[str, Any]:
    sensor_runner.stop("thermal", LAYER8_DIR)
    sensor_runner.stop("webcam", LAYER8_DIR)
    sensor_runner.stop("mmwave", LAYER8_DIR)
    return run_all_sensors()


