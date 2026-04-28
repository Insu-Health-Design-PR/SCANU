#!/usr/bin/env python3
"""
Thermal camera only → MP4 (no mmWave, no Infineon).

Example:
  python3 thermal_only_capture.py --frames 300 --video thermal_out.mp4 --thermal-device 0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Before cv2: reduce V4L2 "can't open camera" warning spam on failure paths.
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import cv2
import numpy as np

_repo_root = Path(__file__).resolve().parents[3]
_software_root = _repo_root / "software"
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_software_root))

from layer1_radar import ThermalCameraSource


def _write_live_frame(path_str: str | None, frame_bgr: np.ndarray) -> None:
    if not path_str:
        return
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(buf.tobytes())
    tmp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Thermal heatmap only → MP4")
    parser.add_argument("--frames", "-n", type=int, default=300)
    parser.add_argument("--fps", type=float, default=10.0)
    parser.add_argument("--video", "-v", default="")
    parser.add_argument("--output", "-o", default=None, help="Optional JSON metrics")
    parser.add_argument("--thermal-device", type=int, default=0)
    parser.add_argument("--thermal-width", type=int, default=640)
    parser.add_argument("--thermal-height", type=int, default=480)
    parser.add_argument("--thermal-fps", type=int, default=30)
    parser.add_argument("--panel-w", type=int, default=640)
    parser.add_argument("--panel-h", type=int, default=480)
    parser.add_argument(
        "--live-frame",
        default="",
        help="Optional path to continuously write latest preview JPG.",
    )
    parser.add_argument(
        "--no-reencode",
        action="store_true",
        help="Skip ffmpeg H.264 step (OpenCV mp4v often won't play in browser/Cursor)",
    )
    args = parser.parse_args()

    W, H = int(args.panel_w), int(args.panel_h)

    try:
        thermal = ThermalCameraSource(
            device=args.thermal_device,
            width=args.thermal_width,
            height=args.thermal_height,
            fps=args.thermal_fps,
        )
    except Exception as exc:
        print(f"ERROR: thermal: {exc}")
        sys.exit(1)

    info = thermal.info()
    print(f"Thermal: {info.width}x{info.height} @ {info.fps:.1f} FPS")

    writer: cv2.VideoWriter | None = None
    video_path = str(args.video or "").strip()
    if video_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(video_path, fourcc, float(args.fps), (W, H))
        if not writer.isOpened():
            thermal.close()
            print(f"ERROR: could not open video writer: {video_path}")
            sys.exit(1)

    frames_out: list[dict] = []
    t0 = time.time()
    wrote_ok = False
    last_good: np.ndarray | None = None
    miss_count = 0

    try:
        i = 0
        infinite = int(args.frames) <= 0
        while infinite or i < int(args.frames):
            heat = thermal.read_colormap_bgr()
            if heat is None:
                miss_count += 1
                # Try reopening after repeated V4L2 timeouts.
                if miss_count >= 20:
                    try:
                        thermal.close()
                    except Exception:
                        pass
                    try:
                        thermal = ThermalCameraSource(
                            device=args.thermal_device,
                            width=args.thermal_width,
                            height=args.thermal_height,
                            fps=args.thermal_fps,
                        )
                        miss_count = 0
                        heat = thermal.read_colormap_bgr()
                    except Exception:
                        heat = None
                if heat is None:
                    if last_good is not None:
                        heat = last_good.copy()
                        cv2.putText(
                            heat,
                            "Thermal frame timeout - showing last frame",
                            (10, H - 14),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.48,
                            (0, 180, 255),
                            1,
                        )
                    else:
                        heat = np.zeros((H, W, 3), dtype=np.uint8)
                        cv2.putText(
                            heat,
                            "No thermal frames (check camera/device index)",
                            (10, max(24, H // 2)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (0, 180, 255),
                            2,
                        )
            else:
                miss_count = 0
                heat = cv2.resize(heat, (W, H), interpolation=cv2.INTER_LINEAR)
                last_good = heat.copy()
            cv2.putText(
                heat,
                "Thermal only",
                (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
            )
            _write_live_frame(args.live_frame, heat)
            if writer is not None:
                writer.write(heat)
            if args.output:
                gray = cv2.cvtColor(heat, cv2.COLOR_BGR2GRAY)
                frames_out.append(
                    {
                        "index": i,
                        "thermal_mean_u8": float(np.mean(gray)) if gray.size else 0.0,
                    }
                )
            dt = time.time() - t0
            fps_live = (i + 1) / dt if dt > 0 else 0.0
            total = "inf" if infinite else str(int(args.frames))
            print(f"\rFrame {i + 1}/{total} | FPS: {fps_live:.1f}", end="")
            i += 1

        if writer is not None:
            print(f"\nSaved: {video_path}")
        if args.output:
            with open(args.output, "w") as f:
                json.dump(frames_out, f, indent=2)
            print(f"JSON: {args.output}")
        wrote_ok = True
    finally:
        if writer is not None:
            writer.release()
        thermal.close()

    if wrote_ok and writer is not None and not args.no_reencode:
        from mp4_web_preview import reencode_mp4_for_web

        reencode_mp4_for_web(video_path)


if __name__ == "__main__":
    main()
