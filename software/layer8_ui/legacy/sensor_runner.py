"""Start/stop capture subprocesses for thermal, Infineon, and mmWave."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Literal

from .thermal_device import detect_working_thermal_device

SensorId = Literal["thermal", "infineon", "mmwave"]

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


def _logs_dir(layer8_dir: Path) -> Path:
    d = layer8_dir / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


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

    if sensor == "infineon":
        i = settings.get("infineon") or {}
        script = ex / "infineon_only_capture.py"
        video = (i.get("video") or "infineon_only.mp4").strip()
        live = (i.get("live_frame") or "").strip()
        out = (i.get("output") or "").strip()
        cmd = [
            py,
            str(script),
            "--frames",
            str(int(i.get("frames", 300))),
            "--fps",
            str(float(i.get("fps", 10))),
            "--video",
            video,
            "--panel-w",
            str(int(i.get("panel_w", 640))),
            "--panel-h",
            str(int(i.get("panel_h", 480))),
        ]
        uuid = (i.get("infineon_uuid") or "").strip()
        if uuid:
            cmd.extend(["--infineon-uuid", uuid])
        if i.get("verbose"):
            cmd.append("--verbose")
        if out:
            cmd.extend(["--output", out])
        if live:
            cmd.extend(["--live-frame", live])
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
    cmd = build_command(sensor, settings, layer8_dir)
    log_path = _logs_dir(layer8_dir) / f"{sensor}.log"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{sw.parent}:{sw}{os.pathsep}{env.get('PYTHONPATH', '')}"

    log_f = open(log_path, "ab", buffering=0)
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(sw),
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
