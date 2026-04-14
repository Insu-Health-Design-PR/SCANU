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

try:
    from layer4_inference import InferenceEngine, ThermalThreatDetector
    from layer4_inference.thermal_detector import draw_detections_on_image
except ImportError:  # pragma: no cover - optional heavy deps
    InferenceEngine = None  # type: ignore[misc, assignment]
    ThermalThreatDetector = None  # type: ignore[misc, assignment]
    draw_detections_on_image = None  # type: ignore[misc, assignment]

try:
    from layer4_inference.safe_unsafe_live import load_safe_unsafe_classifier, predict_safe_unsafe
except ImportError:  # pragma: no cover - optional torch/torchvision
    load_safe_unsafe_classifier = None  # type: ignore[misc, assignment]
    predict_safe_unsafe = None  # type: ignore[misc, assignment]

_THERMAL_CAM_CFG_LEN = 9
_THERMAL_LAYER4_CFG_LEN = 5
_THERMAL_CLF_CFG_LEN = 4


def _layer8_classifier_torch_device(code: int) -> Any:
    """-1 = auto, -2 = CPU, else CUDA device index if available."""
    import torch

    c = int(code)
    if c == -2:
        return torch.device("cpu")
    if c == -1:
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if torch.cuda.is_available():
        return torch.device(f"cuda:{c}")
    return torch.device("cpu")


class _ThermalRunnerClfOverlay:
    """
    Safe/unsafe CNN overlay for ``/api/preview/live/thermal`` (runner-written JPG).

    Separate from :class:`_ThermalSharedStream` so the same checkpoint works while
    capture is running (direct V4L preview is disabled in that mode).
    """

    _lock = threading.Lock()
    _frame = 0
    _key: tuple[str, str] | None = None
    _model: Any = None
    _meta: dict[str, Any] | None = None
    _tfm: Any = None
    _dev: Any = None
    _label = ""
    _conf = 0.0

    @classmethod
    def overlay_jpg(cls, jpg: bytes, settings: dict[str, Any]) -> bytes:
        if (
            load_safe_unsafe_classifier is None
            or predict_safe_unsafe is None
            or not jpg
        ):
            return jpg
        t = settings.get("thermal") or {}
        if not int(t.get("thermal_classifier_enabled", 0)):
            with cls._lock:
                cls._key = None
                cls._model = None
                cls._meta = None
                cls._tfm = None
                cls._dev = None
                cls._label = ""
                cls._conf = 0.0
            return jpg
        rel = str(t.get("thermal_classifier_weights") or "").strip()
        resolved = ""
        if rel:
            p = _resolved_artifact_path(settings, relative_to_software=rel)
            if p is not None and p.is_file():
                resolved = str(p.resolve())
        if not resolved:
            return jpg

        arr = np.frombuffer(jpg, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            return jpg

        every = max(1, int(t.get("thermal_classifier_every_n", 5)))
        dev = _layer8_classifier_torch_device(int(t.get("thermal_classifier_device", -1)))
        ck = (resolved, str(dev))

        with cls._lock:
            cls._frame += 1
            if cls._key != ck:
                try:
                    m, meta, tfm = load_safe_unsafe_classifier(resolved, device=dev)
                    cls._model = m
                    cls._meta = meta
                    cls._tfm = tfm
                    cls._dev = dev
                    cls._key = ck
                except Exception:
                    cls._model = None
                    cls._meta = None
                    cls._tfm = None
                    cls._dev = None
                    cls._key = None
            if cls._model is not None and cls._meta is not None and cls._tfm is not None and cls._dev is not None:
                if cls._frame % every == 0:
                    try:
                        cls._label, cls._conf, _ = predict_safe_unsafe(
                            cls._model,
                            cls._meta,
                            cls._tfm,
                            bgr,
                            device=cls._dev,
                        )
                    except Exception:
                        cls._label = "?"
                        cls._conf = 0.0
            label, conf = cls._label, cls._conf

        if label and label != "?":
            out = bgr.copy()
            color = (40, 40, 255) if label.lower() == "unsafe" else (60, 200, 80)
            cv2.putText(
                out,
                f"{label} {conf:.2f}",
                (12, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                color,
                2,
                cv2.LINE_AA,
            )
            ok, buf = cv2.imencode(".jpg", out, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if ok:
                return buf.tobytes()
        return jpg


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
        # camera (9) + inference (5): see _cfg_from_settings
        self._cfg: tuple[Any, ...] | None = None
        self._cfg_dirty = False
        self._latest_jpg: bytes | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._clients = 0
        self._resolved_device: int | None = None
        self._next_detect_retry_ts = 0.0

    @staticmethod
    def _cfg_from_settings(
        settings: dict[str, Any],
        *,
        thermal_classifier_weights_resolved: str = "",
    ) -> tuple[Any, ...]:
        t = settings.get("thermal") or {}
        requested_device = int(t.get("thermal_device", 0))
        thermal_auto_detect = int(t.get("thermal_auto_detect", 1))
        thermal_detect_max_index = int(t.get("thermal_detect_max_index", 6))
        thermal_detect_retry_s = float(t.get("thermal_detect_retry_s", 12.0))
        thermal_width = int(t.get("thermal_width", 160))
        thermal_height = int(t.get("thermal_height", 120))
        thermal_fps = int(t.get("thermal_fps", 9))
        mid = (t.get("thermal_inference_model_id") or "").strip()
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
            int(t.get("thermal_inference_enabled", 0)),
            int(t.get("thermal_inference_every_n", 3)),
            float(t.get("thermal_inference_threshold", 0.25)),
            int(t.get("thermal_inference_device", -1)),
            mid,
            int(t.get("thermal_classifier_enabled", 0)),
            str(thermal_classifier_weights_resolved),
            int(t.get("thermal_classifier_every_n", 5)),
            int(t.get("thermal_classifier_device", -1)),
        )

    def add_client(self, settings: dict[str, Any]) -> None:
        t = settings.get("thermal") or {}
        rel = str(t.get("thermal_classifier_weights") or "").strip()
        resolved_weights = ""
        if rel:
            p = _resolved_artifact_path(settings, relative_to_software=rel)
            if p is not None and p.is_file():
                resolved_weights = str(p.resolve())
        new_cfg = self._cfg_from_settings(
            settings,
            thermal_classifier_weights_resolved=resolved_weights,
        )
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
        infer_frame = 0
        last_dets: list[Any] = []
        last_src_wh = (1, 1)
        infer_engine: Any | None = None
        infer_key: tuple[str, float, int] | None = None
        clf_frame = 0
        clf_model: Any = None
        clf_meta: dict[str, Any] | None = None
        clf_tfm: Any = None
        clf_dev: Any = None
        clf_key: tuple[str, str] | None = None
        last_clf_label = ""
        last_clf_conf = 0.0
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

                L4 = _THERMAL_CAM_CFG_LEN
                if len(cfg) >= L4 + _THERMAL_LAYER4_CFG_LEN and draw_detections_on_image is not None:
                    ien, ievery, ithresh, idev, imid = cfg[L4 : L4 + _THERMAL_LAYER4_CFG_LEN]
                    if int(ien) and InferenceEngine is not None and ThermalThreatDetector is not None:
                        infer_frame += 1
                        model_id = str(imid).strip() or None
                        key = (model_id or ThermalThreatDetector.DEFAULT_MODEL_ID, float(ithresh), int(idev))
                        if infer_key != key:
                            try:
                                det = ThermalThreatDetector(
                                    model_id=model_id,
                                    threshold=float(ithresh),
                                    device=int(idev),
                                )
                                infer_engine = InferenceEngine(detector=det)
                                infer_key = key
                            except Exception:
                                infer_engine = None
                                infer_key = None
                        if infer_engine is not None and infer_frame % max(1, int(ievery)) == 0:
                            try:
                                bgr_in = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                                h0, w0 = bgr_in.shape[:2]
                                res = infer_engine.infer(infer_frame, time.time() * 1000.0, bgr_in)
                                last_dets = list(res.detections)
                                last_src_wh = (w0, h0)
                            except Exception:
                                last_dets = []
                        if last_dets:
                            draw_detections_on_image(
                                heat,
                                last_dets,
                                box_source_width=last_src_wh[0],
                                box_source_height=last_src_wh[1],
                            )
                    else:
                        last_dets = []
                        infer_engine = None
                        infer_key = None

                clf_base = _THERMAL_CAM_CFG_LEN + _THERMAL_LAYER4_CFG_LEN
                if (
                    len(cfg) >= clf_base + _THERMAL_CLF_CFG_LEN
                    and load_safe_unsafe_classifier is not None
                    and predict_safe_unsafe is not None
                ):
                    cen, cw, cevery, cdev = cfg[clf_base : clf_base + _THERMAL_CLF_CFG_LEN]
                    if int(cen) and cw:
                        clf_frame += 1
                        dev = _layer8_classifier_torch_device(int(cdev))
                        ck = (cw, str(dev))
                        if clf_key != ck:
                            try:
                                clf_model, clf_meta, clf_tfm = load_safe_unsafe_classifier(cw, device=dev)
                                clf_dev = dev
                                clf_key = ck
                            except Exception:
                                clf_model = None
                                clf_meta = None
                                clf_tfm = None
                                clf_dev = None
                                clf_key = None
                        if (
                            clf_model is not None
                            and clf_meta is not None
                            and clf_tfm is not None
                            and clf_dev is not None
                        ):
                            if clf_frame % max(1, int(cevery)) == 0:
                                try:
                                    last_clf_label, last_clf_conf, _ = predict_safe_unsafe(
                                        clf_model,
                                        clf_meta,
                                        clf_tfm,
                                        heat,
                                        device=clf_dev,
                                    )
                                except Exception:
                                    last_clf_label = "?"
                                    last_clf_conf = 0.0
                            if last_clf_label and last_clf_label != "?":
                                color = (
                                    (40, 40, 255)
                                    if last_clf_label.lower() == "unsafe"
                                    else (60, 200, 80)
                                )
                                font = cv2.FONT_HERSHEY_SIMPLEX
                                txt = f"{last_clf_label} {last_clf_conf:.2f}"
                                cv2.putText(heat, txt, (12, 32), font, 0.9, color, 2, cv2.LINE_AA)
                    else:
                        clf_model = None
                        clf_meta = None
                        clf_tfm = None
                        clf_dev = None
                        clf_key = None
                        last_clf_label = ""
                        last_clf_conf = 0.0

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
                    if sensor == "thermal":
                        jpg = _ThermalRunnerClfOverlay.overlay_jpg(jpg, load(LAYER8_DIR))
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


