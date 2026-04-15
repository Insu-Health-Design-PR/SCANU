"""
Webcam live preview (shared V4L2 reader) and weapon-inference subprocess command.

Weapon pipeline runs ``weapon_ai.webcam_layer8_runner`` under ``layer4_inference/``;
that module wraps ``layer4_inference.weapon_ai.infer_thermal_objects`` (see ``inference_overlay``).
"""

from __future__ import annotations

import os
import shlex
import threading
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import cv2

from layer8_ui.artifact_paths import abs_software_path, software_root_from_settings

_WEBCAM_CAM_CFG_LEN = 3


def _webcam_structured_weapon_args(w: dict[str, Any], sw: Path) -> str:
    parts: list[str] = []

    def _f(flag: str, key: str, caster: type) -> None:
        raw = w.get(key)
        if raw is None or str(raw).strip() == "":
            return
        try:
            parts.extend([flag, str(caster(raw))])
        except (TypeError, ValueError):
            return

    _f("--unsafe_threshold", "weapon_unsafe_threshold", float)
    gt_raw = w.get("weapon_gun_threshold")
    if gt_raw is not None and str(gt_raw).strip() != "":
        try:
            if float(gt_raw) > 0:
                parts.extend(["--gun_threshold", str(float(gt_raw))])
        except (TypeError, ValueError):
            pass
    ym = str(w.get("weapon_yolo_model") or "").strip()
    if ym:
        parts.extend(["--yolo_model", ym])
    _f("--conf", "weapon_conf", float)
    _f("--image_size", "weapon_image_size", int)
    _f("--gun_conf", "weapon_gun_conf", float)
    _f("--gun_imgsz", "weapon_gun_imgsz", int)
    _f("--min_box_px", "weapon_min_box_px", int)
    _f("--gun_min_box_px", "weapon_gun_min_box_px", int)
    if int(w.get("weapon_gun_thermal", 0)):
        parts.append("--gun_thermal")
    if int(w.get("weapon_no_gun_yolo", 0)):
        parts.append("--no_gun_yolo")
    if int(w.get("weapon_show_yolo_name", 0)):
        parts.append("--show_yolo_name")
    gpath = str(w.get("weapon_gun_yolo_model") or "").strip()
    if gpath:
        gp = Path(gpath).expanduser()
        abs_g = str(gp.resolve()) if gp.is_absolute() else str((sw / gpath).resolve())
        parts.extend(["--gun_yolo_model", abs_g])

    built = shlex.join(parts) if parts else ""
    manual = (w.get("weapon_extra_args") or "").strip()
    if manual:
        return f"{built} {manual}".strip() if built else manual
    return built


def build_webcam_command(settings: dict[str, Any], layer8_dir: Path) -> list[str]:
    """CLI for ``weapon_ai.webcam_layer8_runner``."""
    import os as _os
    import sys

    del layer8_dir  # cwd/log use paths from settings
    w = settings.get("webcam") or {}
    sw = software_root_from_settings(settings)
    py = _os.environ.get("PYTHON", sys.executable)
    live = abs_software_path(settings, str(w.get("live_frame") or ""))
    if not live:
        raise ValueError("webcam.live_frame must be set (JPEG path under software/).")
    video = abs_software_path(settings, str(w.get("video") or w.get("output") or ""))
    ck = str(w.get("weapon_checkpoint") or "").strip() or (
        "layer4_inference/trained_models/gun_detection/gun_prob_best.pt"
    )
    ck_abs = abs_software_path(settings, ck)
    cmd = [
        py,
        "-m",
        "weapon_ai.webcam_layer8_runner",
        "--webcam-device",
        str(int(w.get("webcam_device", 0))),
        "--checkpoint",
        ck_abs,
        "--live-frame",
        live,
    ]
    if video:
        cmd.extend(["--video", video])
    frames = int(w.get("frames", 0))
    if frames > 0:
        cmd.extend(["--frames", str(frames)])
    extra = _webcam_structured_weapon_args(w, sw).strip()
    if extra:
        cmd.extend(["--weapon-extra-args", extra])
    return cmd


def webcam_command_cwd(settings: dict[str, Any]) -> Path:
    return software_root_from_settings(settings) / "layer4_inference"


class WebcamSharedStream:
    """Single webcam reader shared by MJPEG clients (BGR → JPEG)."""

    def __init__(self, layer8_dir: Path) -> None:
        self._layer8_dir = Path(layer8_dir).resolve()
        self._lock = threading.Lock()
        self._cfg: tuple[Any, ...] | None = None
        self._cfg_dirty = False
        self._latest_jpg: bytes | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._clients = 0

    @property
    def layer8_dir(self) -> Path:
        return self._layer8_dir

    @staticmethod
    def _cfg_from_settings(settings: dict[str, Any]) -> tuple[Any, ...]:
        w = settings.get("webcam") or {}
        t = settings.get("thermal") or {}
        return (
            int(w.get("webcam_device", 0)),
            int(t.get("panel_w", 640)),
            int(t.get("panel_h", 480)),
        )

    def sync_settings(self, settings: dict[str, Any]) -> None:
        new_cfg = self._cfg_from_settings(settings)
        with self._lock:
            if new_cfg == self._cfg:
                return
            self._cfg = new_cfg
            self._cfg_dirty = True

    def add_client(self, settings: dict[str, Any]) -> None:
        new_cfg = self._cfg_from_settings(settings)
        with self._lock:
            self._clients += 1
            if self._cfg != new_cfg:
                self._cfg = new_cfg
                self._cfg_dirty = True
            if self._thread is None or not self._thread.is_alive():
                self._stop_event.clear()
                self._thread = threading.Thread(target=self._run, name="webcam-shared-stream", daemon=True)
                self._thread.start()

    def remove_client(self) -> None:
        with self._lock:
            self._clients = max(0, self._clients - 1)
            if self._clients == 0:
                self._stop_event.set()

    def pause_for_webcam_subprocess(self, join_timeout_s: float = 6.0) -> None:
        with self._lock:
            self._stop_event.set()
        t = self._thread
        if t is not None and t.is_alive():
            t.join(timeout=float(join_timeout_s))

    def resume_after_webcam_subprocess_attempt(self) -> None:
        with self._lock:
            self._stop_event.clear()
            if self._clients > 0 and (self._thread is None or not self._thread.is_alive()):
                self._thread = threading.Thread(target=self._run, name="webcam-shared-stream", daemon=True)
                self._thread.start()

    def latest_jpg(self) -> bytes | None:
        with self._lock:
            return self._latest_jpg

    def _subprocess_running(self) -> bool:
        from layer8_ui import sensor_runner

        return bool(sensor_runner.status("webcam", self._layer8_dir).get("running"))

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

                settings_cam_cfg = cfg[:_WEBCAM_CAM_CFG_LEN]
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
                    device, width, height = settings_cam_cfg
                    cap = cv2.VideoCapture(int(device), cv2.CAP_V4L2)
                    if not cap.isOpened():
                        if cap is not None:
                            cap.release()
                            cap = None
                        next_open_retry_ts = now_ts + 1.5
                        time.sleep(0.1)
                        continue
                    cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
                    cap.set(cv2.CAP_PROP_FPS, 15)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    active_camera_cfg = settings_cam_cfg
                    next_open_retry_ts = 0.0
                    continue

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

                _device, width, height = settings_cam_cfg
                bgr = frame
                if len(bgr.shape) == 2:
                    bgr = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)
                elif bgr.shape[2] == 4:
                    bgr = cv2.cvtColor(bgr, cv2.COLOR_BGRA2BGR)
                preview = cv2.resize(bgr, (int(width), int(height)), interpolation=cv2.INTER_LINEAR)
                ok_enc, jpg = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                if ok_enc:
                    with self._lock:
                        self._latest_jpg = jpg.tobytes()
                time.sleep(0.03)
        finally:
            if cap is not None:
                cap.release()


_webcam_stream: WebcamSharedStream | None = None


def get_webcam_shared_stream(layer8_dir: Path) -> WebcamSharedStream:
    global _webcam_stream
    if _webcam_stream is None:
        _webcam_stream = WebcamSharedStream(Path(layer8_dir))
    return _webcam_stream
