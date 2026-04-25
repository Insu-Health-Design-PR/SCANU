"""
Thermal capture + live preview (shared V4L2 reader, colormap JPEG).

Subprocess entrypoint uses ``layer1_radar.examples.thermal_only_capture`` (same as
``ThermalCameraSource`` pipeline in layer1). Live dashboard reads frames here with OpenCV
when the capture subprocess is not holding the device.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import cv2
import numpy as np

from layer8_ui.artifact_paths import software_root_from_settings
from layer8_ui.thermal_device import detect_working_thermal_device

_THERMAL_CAM_CFG_LEN = 9


def layer1_examples_dir(software_root: Path) -> Path:
    return software_root / "layer1_radar" / "examples"


def thermal_capture_script(software_root: Path) -> Path:
    return layer1_examples_dir(software_root) / "thermal_only_capture.py"


def build_thermal_command(settings: dict[str, Any], _layer8_dir: Path) -> list[str]:
    """CLI for ``thermal_only_capture.py`` (layer1 example)."""
    import os as _os
    import sys

    sw = software_root_from_settings(settings)
    py = _os.environ.get("PYTHON", sys.executable)
    t = settings.get("thermal") or {}
    script = thermal_capture_script(sw)
    video = (t.get("video") or "thermal_only.mp4").strip()
    live = (t.get("live_frame") or "").strip()
    out = (t.get("output") or "").strip()
    thermal_device = int(t.get("thermal_device", 0))
    thermal_auto_detect = bool(int(t.get("thermal_auto_detect", 1)))
    if thermal_auto_detect:
        detected = detect_working_thermal_device(
            preferred=thermal_device,
            width=int(t.get("thermal_width", 640)),
            height=int(t.get("thermal_height", 480)),
            fps=int(t.get("thermal_fps", 30)),
            search_max_index=int(t.get("thermal_detect_max_index", 6)),
        )
        if detected is not None:
            thermal_device = detected

    cmd = [
        py,
        str(script),
        "--frames",
        str(int(t.get("frames", 300))),
        "--fps",
        str(float(t.get("fps", 10))),
        "--video",
        video,
        "--thermal-device",
        str(int(thermal_device)),
        "--thermal-width",
        str(int(t.get("thermal_width", 640))),
        "--thermal-height",
        str(int(t.get("thermal_height", 480))),
        "--thermal-fps",
        str(int(t.get("thermal_fps", 30))),
        "--panel-w",
        str(int(t.get("panel_w", 640))),
        "--panel-h",
        str(int(t.get("panel_h", 480))),
    ]
    if out:
        cmd.extend(["--output", out])
    if live:
        cmd.extend(["--live-frame", live])
    return cmd


def thermal_command_cwd(settings: dict[str, Any]) -> Path:
    return software_root_from_settings(settings)


class ThermalSharedStream:
    """Single thermal camera reader shared by MJPEG / WebSocket clients."""

    def __init__(self, layer8_dir: Path) -> None:
        self._layer8_dir = Path(layer8_dir).resolve()
        self._lock = threading.Lock()
        self._cfg: tuple[Any, ...] | None = None
        self._cfg_dirty = False
        self._latest_jpg: bytes | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._clients = 0
        self._resolved_device: int | None = None
        self._next_detect_retry_ts = 0.0

    @property
    def layer8_dir(self) -> Path:
        return self._layer8_dir

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

    def sync_settings(self, settings: dict[str, Any]) -> None:
        new_cfg = self._cfg_from_settings(settings)
        with self._lock:
            if new_cfg == self._cfg:
                return
            self._cfg = new_cfg
            self._cfg_dirty = True
            self._resolved_device = None
            self._next_detect_retry_ts = 0.0

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

    def pause_for_thermal_subprocess(self, join_timeout_s: float = 6.0) -> None:
        with self._lock:
            self._stop_event.set()
        t = self._thread
        if t is not None and t.is_alive():
            t.join(timeout=float(join_timeout_s))

    def resume_after_thermal_subprocess_attempt(self) -> None:
        with self._lock:
            self._stop_event.clear()
            if self._clients > 0 and (self._thread is None or not self._thread.is_alive()):
                self._thread = threading.Thread(target=self._run, name="thermal-shared-stream", daemon=True)
                self._thread.start()

    def latest_jpg(self) -> bytes | None:
        with self._lock:
            return self._latest_jpg

    def _subprocess_running(self) -> bool:
        from layer8_ui import sensor_runner

        return bool(sensor_runner.status("thermal", self._layer8_dir).get("running"))

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
                    if self._subprocess_running():
                        if cap is not None:
                            try:
                                cap.release()
                            except Exception:
                                pass
                            cap = None
                            active_camera_cfg = None
                        time.sleep(0.18)
                        continue
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
                                self._next_detect_retry_ts = now_ts + max(0.5, float(detect_retry_s))
                            if fallback_device is not None:
                                try_cap = cv2.VideoCapture(int(fallback_device), cv2.CAP_V4L2)
                                if try_cap.isOpened():
                                    cap = try_cap
                                    self._resolved_device = int(fallback_device)
                                else:
                                    try_cap.release()
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

                if self._subprocess_running():
                    if cap is not None:
                        try:
                            cap.release()
                        except Exception:
                            pass
                        cap = None
                        active_camera_cfg = None
                    time.sleep(0.18)
                    continue

                ok, frame = cap.read()
                if not ok or frame is None:
                    time.sleep(0.03)
                    continue

                _, _, _, _, panel_w, panel_h, _a, _b, _c = settings_cam_cfg
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


_thermal_stream: ThermalSharedStream | None = None


def get_thermal_shared_stream(layer8_dir: Path) -> ThermalSharedStream:
    global _thermal_stream
    if _thermal_stream is None:
        _thermal_stream = ThermalSharedStream(Path(layer8_dir))
    return _thermal_stream
