#!/usr/bin/env python3
"""
SCANU Control Panel — terminal menu for sensors, cameras, recording & JSON export.

Usage:
    cd ~/Desktop/SCANU-dev_adrian/software
    source .venv/bin/activate
    python3 layer8_ui/scripts/run.py

The script starts the Layer 8 backend, detects the Tailscale IP, and presents
a menu to start/stop sensors, record video, dump JSON, and view live metrics.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
LAYER8_DIR = SCRIPT_DIR.parent
SOFTWARE_DIR = LAYER8_DIR.parent
PROJECT_DIR = SOFTWARE_DIR.parent
ARTIFACTS_DIR = LAYER8_DIR / "artifacts"
LOG_DIR = LAYER8_DIR / "logs"
BACKEND_HOST = os.environ.get("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8088"))
API_KEY = os.environ.get("LAYER8_API_KEY", "").strip()
BASE_URL = f"http://127.0.0.1:{BACKEND_PORT}"
BACKEND_LOG = LOG_DIR / "backend.menu.log"


# ── helpers ──────────────────────────────────────────────────────────

def _req(method: str, path: str, data: Optional[bytes] = None, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    try:
        headers = {}
        if API_KEY:
            headers["X-Layer8-Api-Key"] = API_KEY
        req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except Exception:
        return None


def api_get(path: str) -> Optional[Dict[str, Any]]:
    return _req("GET", path)


def api_post(path: str) -> Optional[Dict[str, Any]]:
    return _req("POST", path)


def color(text: str, code: int) -> str:
    return f"\033[{code}m{text}\033[0m"


green = lambda t: color(t, 32)
red = lambda t: color(t, 31)
yellow = lambda t: color(t, 33)
cyan = lambda t: color(t, 36)
bold = lambda t: color(t, 1)
dim = lambda t: color(t, 2)


def sensor_icon(st: Optional[Dict[str, Any]]) -> str:
    if st is None:
        return red("● OFFLINE")
    if st.get("running"):
        return green("● RUNNING")
    return yellow("○ STOPPED")


def weapon_badge(metrics: Optional[Dict[str, Any]]) -> str:
    if not metrics:
        return dim("—")
    if metrics.get("gun_detected"):
        return red("⚠ GUN DETECTED")
    conf = float(metrics.get("unsafe_score") or 0)
    if conf > 0.5:
        return red(f"ARMED {conf:.0%}")
    if conf > 0.2:
        return yellow(f"SUSPICIOUS {conf:.0%}")
    return green("CLEAR")


def get_tailscale_ip() -> str:
    try:
        result = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=5)
        ip = result.stdout.strip()
        if ip:
            return ip
    except Exception:
        pass
    return "unknown"


def press_enter():
    input("\nPress Enter to continue...")


# ── backend subprocess ───────────────────────────────────────────────

def start_backend() -> subprocess.Popen:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_DIR}{os.pathsep}{SOFTWARE_DIR}{os.pathsep}{env.get('PYTHONPATH', '')}"
    if API_KEY:
        env["LAYER8_API_KEY"] = API_KEY
    log = BACKEND_LOG.open("ab")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "layer8_ui.app:app",
         "--host", BACKEND_HOST, "--port", str(BACKEND_PORT)],
        cwd=str(SOFTWARE_DIR),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )


def wait_for_backend(timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if api_get("/api/health"):
            return True
        time.sleep(0.3)
    return False


def print_backend_log_tail() -> None:
    if not BACKEND_LOG.is_file():
        print(dim(f"No backend log found at {BACKEND_LOG}"))
        return
    tail = BACKEND_LOG.read_text(errors="replace")[-3000:]
    print(bold(f"\nBackend log tail: {BACKEND_LOG}\n"))
    print(tail)


# ── JSON dump ────────────────────────────────────────────────────────

def dump_json():
    out_dir = ARTIFACTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"snapshot_{ts}.json"

    mmwave_frame = None
    mmwave_path = out_dir / "mmwave_frames.json"
    if mmwave_path.is_file():
        try:
            frames = json.loads(mmwave_path.read_text())
            if frames and isinstance(frames, list):
                mmwave_frame = frames[-10:]  # last 10 frames
        except Exception:
            pass

    metrics = api_get("/api/dashboard/metrics") or {}
    status = api_get("/api/status") or {}
    alerts = api_get("/api/alerts/recent?limit=20") or {}

    payload = {
        "exported_at": ts,
        "tailscale_ip": get_tailscale_ip(),
        "status": status,
        "metrics": metrics,
        "alerts": alerts.get("alerts", []),
        "mmwave_last_10_frames": mmwave_frame,
    }
    path.write_text(json.dumps(payload, indent=2))
    print(green(f"\nJSON saved → {path}"))
    print(f"  Metrics: gun_detected={metrics.get('gun_detected')}, unsafe_score={metrics.get('unsafe_score')}")
    print(f"  Alerts:  {len(payload['alerts'])} recent")
    print(f"  mmWave:  {len(mmwave_frame or [])} frames exported")


# ── recording ────────────────────────────────────────────────────────

def record_clip(seconds: int = 30):
    print(cyan(f"\nRecording {seconds}s clip — starting all sensors..."))
    api_post("/api/run_all")
    print("  Sensors starting...")

    for remaining in range(seconds, 0, -1):
        metrics = api_get("/api/dashboard/metrics") or {}
        gun = "⚠ GUN" if metrics.get("gun_detected") else ""
        print(f"\r  Recording... {remaining:3d}s remaining  {gun}  ", end="")
        time.sleep(1)

    print("\n  Stopping sensors...")
    api_post("/api/stop_all")
    time.sleep(1)

    dump_json()
    print(green(f"\nRecording complete — {seconds}s captured."))


# ── live metrics ─────────────────────────────────────────────────────

def live_metrics():
    print(bold("\nLive metrics — Ctrl+C to stop\n"))
    try:
        while True:
            m = api_get("/api/dashboard/metrics") or {}
            s = api_get("/api/status") or {}
            mm = api_get("/api/status/mmwave") or {}
            wc = api_get("/api/status/webcam") or {}
            th = api_get("/api/status/thermal") or {}

            frame = m.get("frame", "?")
            gun = red("GUN!") if m.get("gun_detected") else green("no")
            persons = m.get("persons_total", "?")
            unsafe = m.get("unsafe_score", 0)
            state = s.get("state", "?")

            print(
                f"\r  Frame:{frame}  State:{cyan(state)}  Gun:{gun}  "
                f"Persons:{persons}  Score:{unsafe:.2f}  "
                f"mmWave:{sensor_icon(mm)}  Webcam:{sensor_icon(wc)}  Thermal:{sensor_icon(th)}  ",
                end="",
            )
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n")


# ── view logs ────────────────────────────────────────────────────────

def view_logs():
    log_dir = LOG_DIR
    sensors = ["mmwave", "webcam", "thermal", "backend", "backend.menu"]
    for name in sensors:
        path = log_dir / f"{name}.log"
        if path.is_file():
            tail = path.read_text(errors="replace")[-1500:]
            print(bold(f"\n─── {name} (last 1500 chars) ───"))
            print(tail[:1500])
        else:
            print(dim(f"\n─── {name} — no log yet"))


# ── main menu ────────────────────────────────────────────────────────

def main():
    ts_ip = get_tailscale_ip()

    backend: Optional[subprocess.Popen] = None
    if api_get("/api/health"):
        print(green("\nSCANU backend already running."))
    else:
        print(bold("\nStarting SCANU backend..."), end=" ", flush=True)
        backend = start_backend()
        if not wait_for_backend():
            print(red("FAILED"))
            if backend.poll() is None:
                backend.kill()
            print_backend_log_tail()
            sys.exit(1)
        print(green("OK"))

    def cleanup():
        print("\nShutting down...")
        api_post("/api/stop_all")
        if backend is not None and backend.poll() is None:
            backend.terminate()
            try:
                backend.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend.kill()
        print("Done.")

    try:
        while True:
            status = api_get("/api/status") or {}
            metrics = api_get("/api/dashboard/metrics") or {}
            mm_s = api_get("/api/status/mmwave") or {}
            wc_s = api_get("/api/status/webcam") or {}
            th_s = api_get("/api/status/thermal") or {}
            state = status.get("state", "?")

            print(f"""
{bold('═' * 52)}
{bold('         SCANU — Control Panel')}
{bold('═' * 52)}
 Backend:  {green('● ONLINE')}  {dim(f'{ts_ip}:{BACKEND_PORT}')}

 {bold('Sensors:')}
   mmWave    {sensor_icon(mm_s)}  [192 chirps, CFAR 6 dB]
   Webcam    {sensor_icon(wc_s)}  [YOLOv8 gun detection]
   Thermal   {sensor_icon(th_s)}
                   
 {bold('Threat:')}  {weapon_badge(metrics)}    {bold('State:')} {cyan(state)}

 {bold('[1]')} Start all     {bold('[2]')} Stop all      {bold('[3]')} Restart all
 {bold('[4]')} mmWave ↕      {bold('[5]')} Webcam ↕      {bold('[6]')} Thermal ↕
 {bold('[R]')} Record 30s    {bold('[D]')} JSON dump     {bold('[M]')} Live metrics
 {bold('[L]')} View logs     {bold('[0]')} Exit
{bold('═' * 52)}
""")
            cmd = input("> ").strip().lower()

            if cmd in ("1", "start"):
                api_post("/api/run_all")
                print("  Starting all sensors...")
            elif cmd in ("2", "stop"):
                api_post("/api/stop_all")
                print("  Stopping all sensors...")
            elif cmd in ("3", "restart"):
                api_post("/api/restart_all")
                print("  Restarting all sensors...")
            elif cmd == "4":
                if mm_s.get("running"):
                    api_post("/api/stop/mmwave")
                else:
                    api_post("/api/run/mmwave")
                print(f"  mmWave toggled")
            elif cmd == "5":
                if wc_s.get("running"):
                    api_post("/api/stop/webcam")
                else:
                    api_post("/api/run/webcam")
                print("  Webcam toggled")
            elif cmd == "6":
                if th_s.get("running"):
                    api_post("/api/stop/thermal")
                else:
                    api_post("/api/run/thermal")
                print("  Thermal toggled")
            elif cmd.lower() == "r":
                record_clip(30)
                press_enter()
            elif cmd.lower() == "d":
                dump_json()
                press_enter()
            elif cmd.lower() == "m":
                live_metrics()
            elif cmd.lower() == "l":
                view_logs()
                press_enter()
            elif cmd in ("0", "exit", "quit", "q"):
                break
            else:
                print(red(f"  Unknown: {cmd}"))
            time.sleep(0.3)

    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
