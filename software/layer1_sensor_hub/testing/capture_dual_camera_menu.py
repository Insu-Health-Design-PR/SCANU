#!/usr/bin/env python3
"""Dual camera capture menu: USB RGB camera + thermal camera.

Features:
- Menu mode: take photo or record video
- Synchronized capture from both cameras
- Auto-named output files
- Manifest logging for traceability
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import cv2
except ModuleNotFoundError:
    cv2 = None  # type: ignore[assignment]

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from software.layer1_sensor_hub.thermal import ThermalCameraSource, normalize_thermal_frame


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Dual camera menu (USB RGB + thermal)")
    p.add_argument("--out-dir", default="~/Desktop/collecting_data/dual_camera", help="Output directory")

    p.add_argument(
        "--rgb-device",
        default="auto",
        help="RGB camera index or 'auto' (default: auto, prefer Logitech/C920)",
    )
    p.add_argument(
        "--list-cameras",
        action="store_true",
        help="List V4L2 cameras and exit",
    )
    p.add_argument("--rgb-width", type=int, default=640)
    p.add_argument("--rgb-height", type=int, default=480)
    p.add_argument("--rgb-fps", type=int, default=30)

    p.add_argument("--thermal-device", type=int, default=1, help="Thermal camera index (/dev/videoX)")
    p.add_argument("--thermal-width", type=int, default=640)
    p.add_argument("--thermal-height", type=int, default=480)
    p.add_argument("--thermal-fps", type=int, default=30)

    p.add_argument("--default-video-seconds", type=float, default=20.0, help="Default video duration")
    p.add_argument("--codec", default="mp4v", help="Video codec fourcc (default: mp4v)")
    p.add_argument("--fps-probe-seconds", type=float, default=1.2, help="Seconds to estimate effective camera FPS")
    return p


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _next_index(out_dir: Path) -> int:
    patt = re.compile(r"^dual_capture_(\d{4})_")
    best = 0
    for p in out_dir.glob("dual_capture_*.json"):
        m = patt.match(p.name)
        if m:
            best = max(best, int(m.group(1)))
    return best + 1


def _base_id(out_dir: Path) -> str:
    idx = _next_index(out_dir)
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"dual_capture_{idx:04d}_{ts}"


def _open_rgb(device: int, width: int, height: int, fps: int):
    if cv2 is None:
        raise RuntimeError("OpenCV (cv2) is required. Install python3-opencv or opencv-python.")
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        # Fallback for systems where index+V4L2 cannot open but CAP_ANY works.
        cap.release()
        cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open RGB camera /dev/video{device}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    return cap


def _read_rgb(cap) -> Optional[object]:
    ok, frame = cap.read()
    if not ok:
        return None
    return frame


def _save_manifest_row(out_dir: Path, row: dict) -> None:
    p = out_dir / "manifest.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=True) + "\n")


def _parse_video_index(dev_path: str) -> Optional[int]:
    m = re.search(r"/dev/video(\d+)$", dev_path.strip())
    if not m:
        return None
    return int(m.group(1))


def _list_v4l2_devices() -> list[dict]:
    """Return parsed camera entries from `v4l2-ctl --list-devices`."""
    try:
        res = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return []

    lines = res.stdout.splitlines()
    entries: list[dict] = []
    current_name = None
    current_nodes: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        if not line.startswith("\t"):
            if current_name is not None and current_nodes:
                entries.append({"name": current_name, "nodes": current_nodes[:]})
            current_name = line.strip().rstrip(":")
            current_nodes = []
            continue
        node = line.strip()
        if node.startswith("/dev/video"):
            current_nodes.append(node)
    if current_name is not None and current_nodes:
        entries.append({"name": current_name, "nodes": current_nodes[:]})
    return entries


def _probe_rgb_index(idx: int) -> bool:
    if cv2 is None:
        return False
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
        try:
            return int(rgb_device_arg)
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid --rgb-device value: {rgb_device_arg}. "
                "Use 'auto', integer index, or /dev/videoX"
            ) from exc

    # 1) Prefer Logitech/C920 from v4l2 listing.
    entries = _list_v4l2_devices()
    preferred: list[int] = []
    fallback: list[int] = []
    for e in entries:
        name = str(e.get("name", "")).lower()
        nodes = e.get("nodes", [])
        indices = [i for n in nodes if (i := _parse_video_index(str(n))) is not None]
        if "logitech" in name or "c920" in name or "webcam" in name:
            preferred.extend(indices)
        else:
            fallback.extend(indices)

    for idx in preferred + fallback:
        if idx == thermal_device:
            continue
        if _probe_rgb_index(idx):
            return idx

    # 2) Final fallback: probe common indices.
    for idx in range(0, 10):
        if idx == thermal_device:
            continue
        if _probe_rgb_index(idx):
            return idx

    raise RuntimeError("Failed to auto-detect RGB camera. Use --rgb-device <index> explicitly.")


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


def _countdown(seconds: int = 3) -> None:
    for n in range(seconds, 0, -1):
        print(f"[PREPARING] Recording starts in {n}...")
        time.sleep(1.0)


def _measure_rgb_fps(cap, seconds: float) -> float:
    if seconds <= 0:
        return 0.0
    start = time.time()
    c = 0
    while time.time() - start < seconds:
        frame = _read_rgb(cap)
        if frame is not None:
            c += 1
    elapsed = max(1e-6, time.time() - start)
    return c / elapsed


def _measure_thermal_fps(thermal: ThermalCameraSource, seconds: float) -> float:
    if seconds <= 0:
        return 0.0
    start = time.time()
    c = 0
    while time.time() - start < seconds:
        frame = thermal.read_colormap_bgr()
        if frame is not None:
            c += 1
    elapsed = max(1e-6, time.time() - start)
    return c / elapsed


def _capture_photo(
    out_dir: Path,
    rgb_cap,
    thermal: ThermalCameraSource,
    rgb_device: int,
    thermal_device: int,
) -> None:
    base = _base_id(out_dir)
    rgb_path = out_dir / f"{base}_rgb.png"
    th_path = out_dir / f"{base}_thermal.png"
    th_gray_path = out_dir / f"{base}_thermal_gray.png"

    rgb = _read_rgb(rgb_cap)
    th_col = thermal.read_colormap_bgr()
    th_raw = thermal.read_raw()
    th_gray = normalize_thermal_frame(th_raw) if th_raw is not None else None

    if rgb is None:
        raise RuntimeError("Failed to read RGB frame")
    if th_col is None:
        raise RuntimeError("Failed to read thermal frame")

    if not cv2.imwrite(str(rgb_path), rgb):
        raise RuntimeError(f"Failed to write RGB image: {rgb_path}")
    if not cv2.imwrite(str(th_path), th_col):
        raise RuntimeError(f"Failed to write thermal image: {th_path}")
    if th_gray is not None:
        _ = cv2.imwrite(str(th_gray_path), th_gray)

    row = {
        "timestamp": datetime.now().isoformat(),
        "type": "photo",
        "base_id": base,
        "rgb_device": rgb_device,
        "thermal_device": thermal_device,
        "rgb_image": str(rgb_path),
        "thermal_image": str(th_path),
        "thermal_gray_image": str(th_gray_path if th_gray is not None else ""),
    }
    _save_manifest_row(out_dir, row)
    print(f"[saved] {rgb_path}")
    print(f"[saved] {th_path}")
    if th_gray is not None:
        print(f"[saved] {th_gray_path}")


def _capture_video(
    out_dir: Path,
    rgb_cap,
    thermal: ThermalCameraSource,
    rgb_device: int,
    thermal_device: int,
    seconds: float,
    codec: str,
    rgb_fps_target: int,
    thermal_fps_target: int,
    fps_probe_seconds: float,
) -> None:
    base = _base_id(out_dir)
    rgb_video = out_dir / f"{base}_rgb.mp4"
    th_video = out_dir / f"{base}_thermal.mp4"
    rgb_snap = out_dir / f"{base}_rgb_snapshot.png"
    th_snap = out_dir / f"{base}_thermal_snapshot.png"

    rgb_frame = _read_rgb(rgb_cap)
    th_frame = thermal.read_colormap_bgr()
    if rgb_frame is None or th_frame is None:
        raise RuntimeError("Cannot start video: failed initial frame read from one or both cameras")

    rgb_h, rgb_w = rgb_frame.shape[:2]
    th_h, th_w = th_frame.shape[:2]

    # Estimate effective FPS to avoid short/fast playback when capture FPS is lower than requested.
    print("[PREPARING] Measuring effective FPS...")
    rgb_fps_measured = _measure_rgb_fps(rgb_cap, float(fps_probe_seconds))
    th_fps_measured = _measure_thermal_fps(thermal, float(fps_probe_seconds))
    rgb_fps_write = max(1.0, min(float(rgb_fps_target), rgb_fps_measured if rgb_fps_measured > 0 else float(rgb_fps_target)))
    th_fps_write = max(1.0, min(float(thermal_fps_target), th_fps_measured if th_fps_measured > 0 else float(thermal_fps_target)))
    print(
        f"[PREPARING] RGB fps target={rgb_fps_target} measured={rgb_fps_measured:.2f} write={rgb_fps_write:.2f} | "
        f"Thermal target={thermal_fps_target} measured={th_fps_measured:.2f} write={th_fps_write:.2f}"
    )

    _countdown(3)
    fourcc = cv2.VideoWriter_fourcc(*codec)
    rgb_writer = cv2.VideoWriter(str(rgb_video), fourcc, float(rgb_fps_write), (rgb_w, rgb_h))
    th_writer = cv2.VideoWriter(str(th_video), fourcc, float(th_fps_write), (th_w, th_h))
    if not rgb_writer.isOpened():
        raise RuntimeError(f"Failed to open RGB video writer: {rgb_video}")
    if not th_writer.isOpened():
        raise RuntimeError(f"Failed to open thermal video writer: {th_video}")

    print(f"[RECORDING] Running for {seconds:.1f}s...")
    start = time.time()
    last_tick = -1
    frame_count = 0
    try:
        while time.time() - start < max(0.5, float(seconds)):
            rgb = _read_rgb(rgb_cap)
            th = thermal.read_colormap_bgr()
            if rgb is None or th is None:
                continue
            rgb_writer.write(rgb)
            th_writer.write(th)
            frame_count += 1
            elapsed = time.time() - start
            tick = int(elapsed)
            if tick != last_tick:
                last_tick = tick
                print(f"[RECORDING] {elapsed:.1f}s / {seconds:.1f}s")
            if frame_count == 1:
                _ = cv2.imwrite(str(rgb_snap), rgb)
                _ = cv2.imwrite(str(th_snap), th)
    finally:
        print("[SAVING] Finalizing video files...")
        rgb_writer.release()
        th_writer.release()

    duration_real = max(0.0, time.time() - start)
    row = {
        "timestamp": datetime.now().isoformat(),
        "type": "video",
        "base_id": base,
        "duration_s_requested": float(seconds),
        "duration_s_recorded": float(duration_real),
        "frames_written": frame_count,
        "rgb_device": rgb_device,
        "thermal_device": thermal_device,
        "rgb_fps_target": int(rgb_fps_target),
        "thermal_fps_target": int(thermal_fps_target),
        "rgb_fps_measured": float(rgb_fps_measured),
        "thermal_fps_measured": float(th_fps_measured),
        "rgb_fps_write": float(rgb_fps_write),
        "thermal_fps_write": float(th_fps_write),
        "rgb_video": str(rgb_video),
        "thermal_video": str(th_video),
        "rgb_snapshot": str(rgb_snap),
        "thermal_snapshot": str(th_snap),
    }
    _save_manifest_row(out_dir, row)
    print(f"[DONE] Saved RGB video: {rgb_video}")
    print(f"[DONE] Saved thermal video: {th_video}")
    print(f"[DONE] Saved RGB snapshot: {rgb_snap}")
    print(f"[DONE] Saved thermal snapshot: {th_snap}")
    print(f"[DONE] Frames written: {frame_count} | duration: {duration_real:.2f}s")


def _menu() -> str:
    print("\n=== Dual Camera Menu ===")
    print("1) Take Photo")
    print("2) Record Video")
    print("3) Exit")
    return input("> ").strip().lower()


def main() -> int:
    args = build_parser().parse_args()
    if cv2 is None:
        raise RuntimeError("cv2 is not installed. Install python3-opencv (Jetson) or opencv-python.")
    if args.list_cameras:
        _print_cameras()
        return 0

    out_dir = _ensure_dir(Path(args.out_dir).expanduser().resolve())

    print("Opening cameras...")
    rgb_device = _detect_rgb_device(str(args.rgb_device), int(args.thermal_device))
    rgb_cap = _open_rgb(rgb_device, args.rgb_width, args.rgb_height, args.rgb_fps)
    thermal = ThermalCameraSource(
        device=args.thermal_device,
        width=args.thermal_width,
        height=args.thermal_height,
        fps=args.thermal_fps,
    )

    # Warmup small buffer for better first captures.
    for _ in range(5):
        _ = _read_rgb(rgb_cap)
        _ = thermal.read_colormap_bgr()

    print(f"Output dir: {out_dir}")
    print(f"RGB camera: /dev/video{rgb_device}")
    print(f"Thermal camera: /dev/video{args.thermal_device}")

    try:
        while True:
            cmd = _menu()
            if cmd in ("3", "exit", "quit", "q"):
                print("Exit.")
                return 0
            if cmd in ("1", "photo", "p"):
                _capture_photo(
                    out_dir=out_dir,
                    rgb_cap=rgb_cap,
                    thermal=thermal,
                    rgb_device=rgb_device,
                    thermal_device=args.thermal_device,
                )
                continue
            if cmd in ("2", "video", "v"):
                raw = input(f"Video seconds (default {args.default_video_seconds}): ").strip()
                secs = float(raw) if raw else float(args.default_video_seconds)
                _capture_video(
                    out_dir=out_dir,
                    rgb_cap=rgb_cap,
                    thermal=thermal,
                    rgb_device=rgb_device,
                    thermal_device=args.thermal_device,
                    seconds=secs,
                    codec=args.codec,
                    rgb_fps_target=args.rgb_fps,
                    thermal_fps_target=args.thermal_fps,
                    fps_probe_seconds=args.fps_probe_seconds,
                )
                continue
            print("Invalid option.")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 0
    finally:
        try:
            rgb_cap.release()
        except Exception:
            pass
        try:
            thermal.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
