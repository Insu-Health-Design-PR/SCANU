"""Start/stop capture subprocesses for thermal, webcam (weapon infer), and mmWave."""

from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Literal

from layer8_ui.thermal_device import detect_working_thermal_device

SensorId = Literal["thermal", "webcam", "mmwave"]

_lock = threading.Lock()
_STATE_PATH: Path | None = None


def _state_path(layer8_dir: Path) -> Path:
    global _STATE_PATH
    if _STATE_PATH is None:
        _STATE_PATH = layer8_dir / ".sensor_pids.json"
    return _STATE_PATH


def _read_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_state(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _software_root(settings: dict[str, Any]) -> Path:
    raw = (settings.get("software_root") or "").strip()
    if raw:
        return Path(raw).resolve()
    return Path(__file__).resolve().parent.parent


def resolved_software_root(settings: dict[str, Any]) -> Path:
    """Absolute `software/` directory used for cwd and PYTHONPATH."""
    return _software_root(settings)


def command_cwd(sensor: SensorId, settings: dict[str, Any]) -> Path:
    """Working directory for the sensor subprocess."""
    sw = _software_root(settings)
    if sensor == "webcam":
        return sw / "layer4_inference"
    return sw


def _abs_software_path(sw: Path, rel: str) -> str:
    rel = rel.strip()
    if not rel:
        return ""
    p = Path(rel).expanduser()
    if p.is_absolute():
        return str(p.resolve())
    return str((sw / p).resolve())


def _webcam_structured_weapon_args(w: dict, sw: Path) -> str:
    """Build extra CLI for infer_thermal_objects from settings (merged with weapon_extra_args)."""
    parts: list[str] = []

    def _f(flag: str, key: str, caster) -> None:
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


def build_command(sensor: SensorId, settings: dict[str, Any], layer8_dir: Path) -> list[str]:
    sw = _software_root(settings)
    py = os.environ.get("PYTHON", sys.executable)
    ex = sw / "layer1_radar" / "examples"

    if sensor == "thermal":
        t = settings.get("thermal") or {}
        script = ex / "thermal_only_capture.py"
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

    if sensor == "webcam":
        w = settings.get("webcam") or {}
        sw = _software_root(settings)
        live = _abs_software_path(sw, str(w.get("live_frame") or ""))
        if not live:
            raise ValueError("webcam.live_frame must be set (JPEG path under software/).")
        video = _abs_software_path(sw, str(w.get("video") or w.get("output") or ""))
        ck = str(w.get("weapon_checkpoint") or "").strip() or (
            "layer4_inference/trained_models/gun_detection/gun_prob_best.pt"
        )
        ck_abs = _abs_software_path(sw, ck)
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

    # mmwave
    m = settings.get("mmwave") or {}
    script = ex / "live_capture.py"
    cmd = [py, str(script), "--frames", str(int(m.get("frames", 100)))]
    mmwave_only = bool(int(m.get("mmwave_only", 1)))
    if mmwave_only:
        cmd.append("--mmwave-only")
    cfg = (m.get("config") or "").strip()
    if cfg:
        cmd.extend(["--config", cfg])
    cli = (m.get("cli_port") or "").strip()
    if cli:
        cmd.extend(["--cli-port", cli])
    data = (m.get("data_port") or "").strip()
    if data:
        cmd.extend(["--data-port", data])
    out = (m.get("output") or "").strip()
    if out:
        cmd.extend(["--output", out])
    video = (m.get("video") or "").strip()
    if video:
        cmd.extend(["--video", video])
    live = (m.get("live_frame") or "").strip()
    if live:
        cmd.extend(["--live-frame", live])
    timeout = m.get("no_frame_timeout_s")
    if timeout is not None and float(timeout) > 0:
        cmd.extend(["--no-frame-timeout-s", str(float(timeout))])
    if m.get("verbose"):
        cmd.append("--verbose")
    extra = (m.get("extra_args") or "").strip()
    if extra:
        import shlex

        cmd.extend(shlex.split(extra))
    return cmd


def status(sensor: SensorId, layer8_dir: Path) -> dict[str, Any]:
    path = _state_path(layer8_dir)
    with _lock:
        st = _read_state(path)
    entry = st.get(sensor) or {}
    pid = int(entry.get("pid") or 0)
    running = _pid_alive(pid)
    if not running and pid:
        with _lock:
            st = _read_state(path)
            if st.get(sensor, {}).get("pid") == pid:
                st.pop(sensor, None)
                _write_state(path, st)
        pid = 0
    log_file = entry.get("log_file")
    tail = ""
    if log_file and Path(log_file).is_file():
        try:
            raw = Path(log_file).read_bytes()
            tail = raw[-4000:].decode("utf-8", errors="replace")
        except OSError:
            tail = ""
    return {"running": running, "pid": pid, "log_tail": tail, "log_file": log_file or ""}


def stop(sensor: SensorId, layer8_dir: Path) -> dict[str, Any]:
    path = _state_path(layer8_dir)
    with _lock:
        st = _read_state(path)
        entry = st.get(sensor) or {}
        pid = int(entry.get("pid") or 0)
    if pid and _pid_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    with _lock:
        st = _read_state(path)
        st.pop(sensor, None)
        _write_state(path, st)
    return {"ok": True, "stopped_pid": pid}


def start(sensor: SensorId, settings: dict[str, Any], layer8_dir: Path) -> dict[str, Any]:
    path = _state_path(layer8_dir)
    cur = status(sensor, layer8_dir)
    if cur["running"]:
        return {"ok": False, "error": f"{sensor} already running (pid {cur['pid']})"}

    sw = _software_root(settings)
    try:
        cmd = build_command(sensor, settings, layer8_dir)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    cwd = command_cwd(sensor, settings)
    log_path = _logs_dir(layer8_dir) / f"{sensor}.log"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{sw.parent}:{sw}{os.pathsep}{env.get('PYTHONPATH', '')}"

    log_f = open(log_path, "ab", buffering=0)
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=log_f,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
    except OSError as e:
        log_f.close()
        return {"ok": False, "error": str(e)}
    log_f.close()

    with _lock:
        st = _read_state(path)
        st[sensor] = {"pid": proc.pid, "log_file": str(log_path)}
        _write_state(path, st)

    return {
        "ok": True,
        "pid": proc.pid,
        "command": cmd,
        "cwd": str(sw),
        "log_file": str(log_path),
    }


def restart(sensor: SensorId, settings: dict[str, Any], layer8_dir: Path) -> dict[str, Any]:
    stop(sensor, layer8_dir)
    return start(sensor, settings, layer8_dir)
