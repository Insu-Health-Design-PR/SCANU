#!/usr/bin/env python3
"""Guided 4-scenario multisensor capture.

Captures RGB + thermal + mmWave + presence and writes one composite image per
scenario showing all sensor views together:
- RGB camera
- Thermal camera
- mmWave point cloud panel
- Presence signal panel

Scenarios:
1) empty_room
2) person_unarmed
3) person_armed_concealed
4) person_armed_visible
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from software.layer1_sensor_hub.infeneon import IfxLtr11PresenceProvider, MockPresenceProvider, PresenceSource
from software.layer1_sensor_hub.mmwave import RadarConfigurator, SerialManager, TLVParser, UARTSource
from software.layer1_sensor_hub.thermal import ThermalCameraSource

SCENARIOS: list[tuple[str, str]] = [
    ("empty_room", "Room only (no person)"),
    ("person_unarmed", "Person unarmed"),
    ("person_armed_concealed", "Person with concealed weapon"),
    ("person_armed_visible", "Person with visible weapon"),
]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="4-scenario multisensor capture (RGB + thermal + mmWave + presence)")
    p.add_argument("--out-dir", default="~/Desktop/collecting_data/four_scenario_multisensor", help="Output directory")
    p.add_argument("--session", default="session", help="Session tag used in file names")

    p.add_argument("--capture-seconds", type=float, default=8.0, help="Capture duration for each scenario")
    p.add_argument("--interval-s", type=float, default=0.1, help="Loop delay")
    p.add_argument("--mmwave-timeout-ms", type=int, default=200, help="mmWave read timeout")

    p.add_argument("--rgb-device", default="auto", help="RGB camera index, /dev/videoX, or auto")
    p.add_argument("--rgb-width", type=int, default=640)
    p.add_argument("--rgb-height", type=int, default=480)
    p.add_argument("--rgb-fps", type=int, default=30)

    p.add_argument("--thermal-device", type=int, default=0)
    p.add_argument("--thermal-width", type=int, default=640)
    p.add_argument("--thermal-height", type=int, default=480)
    p.add_argument("--thermal-fps", type=int, default=30)

    p.add_argument("--cli-port", default=None, help="mmWave CLI port (optional, auto when omitted)")
    p.add_argument("--data-port", default=None, help="mmWave DATA port (optional, auto when omitted)")
    p.add_argument(
        "--config",
        default="software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_sensitivity.cfg",
        help="mmWave cfg path",
    )
    p.add_argument("--skip-mmwave-config", action="store_true", help="Skip sending mmWave cfg")

    p.add_argument("--presence", choices=("ifx", "mock", "off"), default="ifx", help="Presence source")
    p.add_argument("--ifx-uuid", default=None, help="Optional Infineon UUID")

    p.add_argument("--panel-width", type=int, default=640)
    p.add_argument("--panel-height", type=int, default=480)
    p.add_argument(
        "--capture-mode",
        choices=("image", "video", "both"),
        default="both",
        help="Per-scenario output mode",
    )
    p.add_argument("--video-codec", default="mp4v", help="Composite video fourcc codec")
    p.add_argument("--video-fps", type=float, default=10.0, help="Composite video FPS")
    p.add_argument("--no-prompt", action="store_true", help="Run all scenarios without Enter prompts")
    p.add_argument("--list-cameras", action="store_true", help="List V4L2 camera devices and exit")
    return p


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate
    cwd_candidate = (Path.cwd() / candidate).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (REPO_ROOT / candidate).resolve()


def _parse_video_index(dev_path: str) -> Optional[int]:
    m = re.search(r"/dev/video(\d+)$", dev_path.strip())
    if not m:
        return None
    return int(m.group(1))


def _list_v4l2_devices() -> list[dict]:
    try:
        res = subprocess.run(["v4l2-ctl", "--list-devices"], check=True, capture_output=True, text=True)
    except Exception:
        return []

    entries: list[dict] = []
    cur_name: Optional[str] = None
    cur_nodes: list[str] = []
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        if not line.startswith("\t"):
            if cur_name is not None and cur_nodes:
                entries.append({"name": cur_name, "nodes": cur_nodes[:]})
            cur_name = line.strip().rstrip(":")
            cur_nodes = []
        else:
            node = line.strip()
            if node.startswith("/dev/video"):
                cur_nodes.append(node)
    if cur_name is not None and cur_nodes:
        entries.append({"name": cur_name, "nodes": cur_nodes[:]})
    return entries


def _print_cameras() -> None:
    entries = _list_v4l2_devices()
    if not entries:
        print("No V4L2 camera list available (v4l2-ctl missing or no devices).")
        return
    print("Detected V4L2 camera devices:")
    for e in entries:
        print(f"- {e['name']}")
        for n in e["nodes"]:
            print(f"  - {n}")


def _probe_rgb_index(idx: int) -> bool:
    cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(idx)
    if not cap.isOpened():
        cap.release()
        return False
    ok, frame = cap.read()
    cap.release()
    return bool(ok and frame is not None and getattr(frame, "size", 0) > 0)


def _detect_rgb_device(rgb_device_arg: str, thermal_device: int) -> int:
    if rgb_device_arg.lower() != "auto":
        maybe_idx = _parse_video_index(rgb_device_arg)
        if maybe_idx is not None:
            return maybe_idx
        return int(rgb_device_arg)

    entries = _list_v4l2_devices()
    preferred: list[int] = []
    fallback: list[int] = []
    for e in entries:
        name = str(e.get("name", "")).lower()
        indices = [i for n in e.get("nodes", []) if (i := _parse_video_index(str(n))) is not None]
        if "logitech" in name or "c920" in name or "webcam" in name:
            preferred.extend(indices)
        else:
            fallback.extend(indices)

    for idx in preferred + fallback:
        if idx == thermal_device:
            continue
        if _probe_rgb_index(idx):
            return idx

    for idx in range(0, 10):
        if idx == thermal_device:
            continue
        if _probe_rgb_index(idx):
            return idx

    raise RuntimeError("Failed to auto-detect RGB camera. Use --rgb-device /dev/videoX")


def _open_rgb(device: int, width: int, height: int, fps: int):
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open RGB camera /dev/video{device}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    return cap


def _read_rgb(cap) -> Optional[np.ndarray]:
    ok, frame = cap.read()
    if not ok:
        return None
    return frame


def _next_index(out_dir: Path, session_tag: str) -> int:
    patt = re.compile(rf"^{re.escape(session_tag)}_(\d{{4}})_")
    best = 0
    for p in out_dir.glob(f"{session_tag}_*_composite.png"):
        m = patt.match(p.stem)
        if m:
            best = max(best, int(m.group(1)))
    return best + 1


def _scenario_slug_label_pairs() -> list[tuple[str, str]]:
    return SCENARIOS[:]


def _build_presence_source(mode: str, ifx_uuid: Optional[str]) -> Optional[PresenceSource]:
    if mode == "off":
        return None
    if mode == "mock":
        return PresenceSource(MockPresenceProvider())
    return PresenceSource(IfxLtr11PresenceProvider(uuid=ifx_uuid))


def _connect_mmwave(serial_mgr: SerialManager, cli_port: Optional[str], data_port: Optional[str]) -> tuple[str, str]:
    candidates: list[tuple[str, str]] = []
    if cli_port and data_port:
        candidates.append((str(cli_port), str(data_port)))
        if str(cli_port) != str(data_port):
            candidates.append((str(data_port), str(cli_port)))
    else:
        ports = serial_mgr.find_radar_ports(verbose=False, config_port=cli_port, data_port=data_port)
        candidates.append((ports.config_port, ports.data_port))
        if ports.config_port != ports.data_port:
            candidates.append((ports.data_port, ports.config_port))

    errors: list[str] = []
    chosen: Optional[tuple[str, str]] = None
    for cfg, dat in candidates:
        alive = False
        try:
            serial_mgr.connect(cfg, dat)
            alive, _ = serial_mgr.probe_cli(timeout_s=1.0)
            if alive:
                chosen = (cfg, dat)
                break
            errors.append(f"{cfg}/{dat}: CLI did not respond")
        except Exception as exc:
            errors.append(f"{cfg}/{dat}: {exc}")
        finally:
            if alive:
                continue
            if not serial_mgr.is_connected:
                continue
            try:
                serial_mgr.disconnect()
            except Exception:
                pass
    if chosen is not None:
        return chosen
    raise RuntimeError(f"Failed mmWave connect/probe. Tried: {errors}")


def render_radar_panel(width: int, height: int, parsed_frame: Optional[object]) -> np.ndarray:
    panel = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.putText(panel, "mmWave Point Cloud", (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

    center_x = width // 2
    bottom_y = height - 30
    meters_to_px = max(40, min(width, height) // 6)

    cv2.line(panel, (center_x, bottom_y), (center_x, 45), (70, 70, 70), 1)
    cv2.line(panel, (40, bottom_y), (width - 40, bottom_y), (70, 70, 70), 1)

    points = getattr(parsed_frame, "points", []) if parsed_frame is not None else []
    points = points or []
    for p in points:
        x_m = float(getattr(p, "x", 0.0))
        y_m = float(getattr(p, "y", 0.0))
        px = int(center_x + x_m * meters_to_px)
        py = int(bottom_y - y_m * meters_to_px)
        if 0 <= px < width and 0 <= py < height:
            cv2.circle(panel, (px, py), 4, (0, 220, 255), -1)

    cv2.putText(panel, f"points: {len(points)}", (10, height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 2)
    return panel


def render_presence_panel(width: int, height: int, presence_hist: deque[float], motion_hist: deque[float]) -> np.ndarray:
    panel = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.putText(panel, "Presence Sensor", (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
    if not presence_hist:
        cv2.putText(panel, "no data", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (180, 180, 180), 2)
        return panel

    p = np.asarray(presence_hist, dtype=np.float32)
    m = np.asarray(motion_hist, dtype=np.float32) if len(motion_hist) == len(presence_hist) else np.zeros_like(p)
    max_v = float(np.percentile(p, 98)) if p.size >= 5 else float(np.max(p))
    max_v = max(max_v, 1e-6)
    norm = np.clip(p / max_v, 0.0, 1.0)

    left, right = 10, width - 10
    top, bottom = 80, height - 20
    cv2.rectangle(panel, (left, top), (right, bottom), (70, 70, 70), 1)
    xs = np.linspace(left, right, norm.size, dtype=np.int32)
    ys = (bottom - norm * (bottom - top)).astype(np.int32)
    pts = np.column_stack([xs, ys]).reshape((-1, 1, 2))
    cv2.polylines(panel, [pts], isClosed=False, color=(0, 200, 255), thickness=2)

    cur_p = float(p[-1])
    cur_m = float(m[-1])
    cv2.putText(panel, f"presence_raw: {cur_p:.5f}", (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 2)
    motion_color = (0, 255, 0) if cur_m >= 0.5 else (90, 90, 90)
    cv2.circle(panel, (right - 15, 52), 10, motion_color, -1)
    cv2.putText(panel, "motion", (right - 95, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (210, 210, 210), 2)
    return panel


def _composite_image(
    rgb: np.ndarray,
    thermal: np.ndarray,
    radar_panel: np.ndarray,
    presence_panel: np.ndarray,
    scenario_slug: str,
    scenario_label: str,
    elapsed_s: float,
) -> np.ndarray:
    top = np.hstack((rgb, thermal))
    bottom = np.hstack((radar_panel, presence_panel))
    comp = np.vstack((top, bottom))

    cv2.rectangle(comp, (0, 0), (comp.shape[1], 42), (0, 0, 0), -1)
    title = f"{scenario_slug} | {scenario_label} | captured={elapsed_s:.1f}s"
    cv2.putText(comp, title, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
    return comp


def _save_manifest_row(out_dir: Path, row: dict) -> None:
    p = out_dir / "manifest.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=True) + "\n")


def _capture_single_scenario(
    scenario_slug: str,
    scenario_label: str,
    out_dir: Path,
    session_tag: str,
    seq: int,
    capture_seconds: float,
    interval_s: float,
    mmwave_timeout_ms: int,
    panel_w: int,
    panel_h: int,
    capture_mode: str,
    video_codec: str,
    video_fps: float,
    rgb_cap,
    thermal: ThermalCameraSource,
    uart_src: UARTSource,
    tlv_parser: TLVParser,
    presence_source: Optional[PresenceSource],
    rgb_device: int,
    thermal_device: int,
    cli_port: str,
    data_port: str,
) -> None:
    now = datetime.now().strftime("%Y%m%dT%H%M%S")
    base = f"{session_tag}_{seq:04d}_{scenario_slug}_{now}"

    composite_video_path = out_dir / f"{base}_composite.mp4"
    video_writer = None

    p_hist: deque[float] = deque(maxlen=300)
    m_hist: deque[float] = deque(maxlen=300)

    last_rgb: Optional[np.ndarray] = None
    last_th: Optional[np.ndarray] = None
    best_mm = None
    best_mm_points = -1
    last_presence = None

    frame_samples: list[dict] = []

    print(f"[CAPTURE] {scenario_slug}: recording {capture_seconds:.1f}s ...")
    if capture_mode in ("video", "both"):
        fourcc = cv2.VideoWriter_fourcc(*str(video_codec))
        fps_write = float(video_fps) if float(video_fps) > 0 else max(1.0, 1.0 / max(interval_s, 0.01))
        video_writer = cv2.VideoWriter(str(composite_video_path), fourcc, fps_write, (panel_w * 2, panel_h * 2))
        if not video_writer.isOpened():
            raise RuntimeError(f"Failed to open composite video writer: {composite_video_path}")

    start = time.time()
    i = 0
    while time.time() - start < max(0.5, float(capture_seconds)):
        t = time.time()
        mm_parsed = None
        raw = uart_src.read_frame(timeout_ms=mmwave_timeout_ms)
        if raw is not None:
            mm_parsed = tlv_parser.parse(raw)

        rgb = _read_rgb(rgb_cap)
        if rgb is not None:
            rgb = cv2.resize(rgb, (panel_w, panel_h), interpolation=cv2.INTER_LINEAR)
            cv2.putText(rgb, "RGB Camera", (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
            last_rgb = rgb

        th = thermal.read_colormap_bgr()
        if th is not None:
            th = cv2.resize(th, (panel_w, panel_h), interpolation=cv2.INTER_LINEAR)
            cv2.putText(th, "Thermal Camera", (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
            last_th = th

        prs = None
        if presence_source is not None:
            try:
                prs = presence_source.read_frame()
                p_hist.append(float(prs.presence_raw))
                m_hist.append(float(prs.motion_raw))
                last_presence = prs
            except Exception:
                pass

        pts_n = len(getattr(mm_parsed, "points", []) or []) if mm_parsed is not None else 0
        if mm_parsed is not None and pts_n >= best_mm_points:
            best_mm = mm_parsed
            best_mm_points = pts_n

        disp_rgb = rgb if rgb is not None else last_rgb
        if disp_rgb is None:
            disp_rgb = np.zeros((panel_h, panel_w, 3), dtype=np.uint8)
            cv2.putText(disp_rgb, "RGB Camera (no frame)", (20, panel_h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)

        disp_th = th if th is not None else last_th
        if disp_th is None:
            disp_th = np.zeros((panel_h, panel_w, 3), dtype=np.uint8)
            cv2.putText(disp_th, "Thermal Camera (no frame)", (20, panel_h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)

        radar_now = render_radar_panel(panel_w, panel_h, mm_parsed if mm_parsed is not None else best_mm)
        presence_now = render_presence_panel(panel_w, panel_h, p_hist, m_hist)
        composite_now = _composite_image(
            disp_rgb,
            disp_th,
            radar_now,
            presence_now,
            scenario_slug,
            scenario_label,
            max(0.0, time.time() - start),
        )
        if video_writer is not None:
            video_writer.write(composite_now)

        frame_samples.append(
            {
                "frame_idx": i,
                "timestamp_ms": t * 1000.0,
                "mmwave_points": int(pts_n),
                "presence_raw": None if prs is None else float(prs.presence_raw),
                "motion_raw": None if prs is None else float(prs.motion_raw),
            }
        )

        i += 1
        if interval_s > 0:
            time.sleep(interval_s)

    elapsed = max(0.0, time.time() - start)
    if video_writer is not None:
        video_writer.release()

    if last_rgb is None:
        last_rgb = np.zeros((panel_h, panel_w, 3), dtype=np.uint8)
        cv2.putText(last_rgb, "RGB Camera (no frame)", (20, panel_h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)
    if last_th is None:
        last_th = np.zeros((panel_h, panel_w, 3), dtype=np.uint8)
        cv2.putText(last_th, "Thermal Camera (no frame)", (20, panel_h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)

    radar_panel = render_radar_panel(panel_w, panel_h, best_mm)
    presence_panel = render_presence_panel(panel_w, panel_h, p_hist, m_hist)
    composite = _composite_image(last_rgb, last_th, radar_panel, presence_panel, scenario_slug, scenario_label, elapsed)

    composite_path = out_dir / f"{base}_composite.png"
    rgb_path = out_dir / f"{base}_rgb.png"
    thermal_path = out_dir / f"{base}_thermal.png"
    radar_path = out_dir / f"{base}_radar.png"
    presence_path = out_dir / f"{base}_presence.png"
    json_path = out_dir / f"{base}_capture.json"

    if capture_mode in ("image", "both"):
        if not cv2.imwrite(str(composite_path), composite):
            raise RuntimeError(f"Failed to write: {composite_path}")
    _ = cv2.imwrite(str(rgb_path), last_rgb)
    _ = cv2.imwrite(str(thermal_path), last_th)
    _ = cv2.imwrite(str(radar_path), radar_panel)
    _ = cv2.imwrite(str(presence_path), presence_panel)

    record = {
        "timestamp": datetime.now().isoformat(),
        "base_id": base,
        "scenario": scenario_slug,
        "scenario_label": scenario_label,
        "capture_seconds": float(elapsed),
        "frames": len(frame_samples),
        "rgb_device": f"/dev/video{rgb_device}",
        "thermal_device": f"/dev/video{thermal_device}",
        "mmwave_cli_port": cli_port,
        "mmwave_data_port": data_port,
        "presence_mode": "off" if presence_source is None else "enabled",
        "last_presence": None
        if last_presence is None
        else {
            "frame_number": int(last_presence.frame_number),
            "presence_raw": float(last_presence.presence_raw),
            "motion_raw": float(last_presence.motion_raw),
            "distance_m": None if float(last_presence.distance_m) < 0 else float(last_presence.distance_m),
        },
        "best_mmwave": {
            "frame_number": None if best_mm is None else getattr(best_mm, "frame_number", None),
            "points": int(best_mm_points if best_mm_points > 0 else 0),
        },
        "outputs": {
            "composite_image": str(composite_path if capture_mode in ("image", "both") else ""),
            "composite_video": str(composite_video_path if capture_mode in ("video", "both") else ""),
            "rgb_image": str(rgb_path),
            "thermal_image": str(thermal_path),
            "radar_panel": str(radar_path),
            "presence_panel": str(presence_path),
        },
        "frame_samples": frame_samples,
    }

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    _save_manifest_row(
        out_dir,
        {
            "timestamp": datetime.now().isoformat(),
            "base_id": base,
            "scenario": scenario_slug,
            "composite_image": str(composite_path if capture_mode in ("image", "both") else ""),
            "composite_video": str(composite_video_path if capture_mode in ("video", "both") else ""),
            "capture_json": str(json_path),
        },
    )

    if capture_mode in ("image", "both"):
        print(f"[SAVED] {composite_path}")
    if capture_mode in ("video", "both"):
        print(f"[SAVED] {composite_video_path}")
    print(f"[SAVED] {json_path}")


def main() -> int:
    args = build_parser().parse_args()

    if args.list_cameras:
        _print_cameras()
        return 0

    out_dir = _ensure_dir(Path(args.out_dir).expanduser().resolve())
    cfg_path = _resolve_path(args.config)
    if not args.skip_mmwave_config and not cfg_path.exists():
        raise RuntimeError(f"mmWave cfg not found: {cfg_path}")

    serial_mgr = SerialManager()
    rgb_cap = None
    thermal = None
    presence_source: Optional[PresenceSource] = None

    print("[INIT] Opening sensors...")
    try:
        rgb_idx = _detect_rgb_device(str(args.rgb_device), int(args.thermal_device))
        rgb_cap = _open_rgb(rgb_idx, args.rgb_width, args.rgb_height, args.rgb_fps)
        thermal = ThermalCameraSource(
            device=args.thermal_device,
            width=args.thermal_width,
            height=args.thermal_height,
            fps=args.thermal_fps,
        )

        used_cli, used_data = _connect_mmwave(serial_mgr, args.cli_port, args.data_port)
        print(f"[INIT] mmWave ports CLI={used_cli} DATA={used_data}")

        if not args.skip_mmwave_config:
            cfg_result = RadarConfigurator(serial_mgr).configure_from_file(cfg_path)
            if not cfg_result.success:
                raise RuntimeError(f"mmWave cfg failed: {cfg_result.errors[:5]}")

        uart = UARTSource(serial_mgr)
        parser = TLVParser()
        serial_mgr.flush_data_port()
        uart.clear_buffer()

        try:
            presence_source = _build_presence_source(args.presence, args.ifx_uuid)
        except Exception as exc:
            print(f"[WARN] Presence init failed ({exc}). Continuing with presence OFF.")
            presence_source = None

        print(f"[INIT] Output dir: {out_dir}")
        print(f"[INIT] RGB camera: /dev/video{rgb_idx}")
        print(f"[INIT] Thermal camera: /dev/video{args.thermal_device}")

        seq = _next_index(out_dir, args.session)
        scenarios = _scenario_slug_label_pairs()

        for idx, (slug, label) in enumerate(scenarios, start=1):
            print("\n" + "=" * 72)
            print(f"Scenario {idx}/4: {slug} -> {label}")
            if not args.no_prompt:
                user = input("Press Enter to start (s=skip, q=quit): ").strip().lower()
                if user in ("q", "quit", "exit"):
                    print("[STOP] User exit.")
                    break
                if user in ("s", "skip"):
                    print(f"[SKIP] {slug}")
                    continue

            _capture_single_scenario(
                scenario_slug=slug,
                scenario_label=label,
                out_dir=out_dir,
                session_tag=args.session,
                seq=seq,
                capture_seconds=float(args.capture_seconds),
                interval_s=float(args.interval_s),
                mmwave_timeout_ms=int(args.mmwave_timeout_ms),
                panel_w=int(args.panel_width),
                panel_h=int(args.panel_height),
                capture_mode=str(args.capture_mode),
                video_codec=str(args.video_codec),
                video_fps=float(args.video_fps),
                rgb_cap=rgb_cap,
                thermal=thermal,
                uart_src=uart,
                tlv_parser=parser,
                presence_source=presence_source,
                rgb_device=rgb_idx,
                thermal_device=int(args.thermal_device),
                cli_port=used_cli,
                data_port=used_data,
            )
            seq += 1

        print("\n[DONE] Four-scenario multisensor capture finished.")
        print(f"[DONE] Manifest: {out_dir / 'manifest.jsonl'}")
        return 0

    finally:
        if rgb_cap is not None:
            try:
                rgb_cap.release()
            except Exception:
                pass
        if thermal is not None:
            try:
                thermal.close()
            except Exception:
                pass
        if presence_source is not None:
            provider = getattr(presence_source, "_provider", None)
            close_fn = getattr(provider, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    pass
        if serial_mgr.is_connected:
            try:
                RadarConfigurator(serial_mgr).stop()
            except Exception:
                pass
            try:
                serial_mgr.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
