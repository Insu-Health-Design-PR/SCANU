#!/usr/bin/env python3
"""Capture thermal camera stream and save MP4 + optional PNG snapshot."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    import cv2
    from software.layer1_sensor_hub.thermal import ThermalCameraSource

    p = argparse.ArgumentParser(description="Capture thermal video from layer1_sensor_hub thermal source")
    p.add_argument("--device", type=int, default=0)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--seconds", type=float, default=12.0)
    p.add_argument("--video", default="thermal_capture.mp4")
    p.add_argument("--snapshot", default="thermal_snapshot.png")
    args = p.parse_args()

    src = ThermalCameraSource(device=args.device, width=args.width, height=args.height, fps=args.fps)
    writer = None
    last = None
    start = time.time()
    frames = 0
    try:
        info = src.info()
        out_w = int(info.width) if info.width > 0 else int(args.width)
        out_h = int(info.height) if info.height > 0 else int(args.height)
        out_fps = float(info.fps) if info.fps > 0 else float(args.fps)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.video, fourcc, out_fps, (out_w, out_h))
        if not writer.isOpened():
            raise RuntimeError(f"Could not open video writer: {args.video}")

        while (time.time() - start) < float(args.seconds):
            frame = src.read_colormap_bgr()
            if frame is None:
                time.sleep(0.01)
                continue
            if frame.shape[1] != out_w or frame.shape[0] != out_h:
                frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_LINEAR)
            writer.write(frame)
            last = frame
            frames += 1
            print(f"\rCaptured thermal frames: {frames}", end="")

        print()
        if last is not None:
            cv2.imwrite(args.snapshot, last)
            print(f"Saved snapshot: {Path(args.snapshot).resolve()}")
        print(f"Saved video: {Path(args.video).resolve()}")
        return 0
    finally:
        if writer is not None:
            try:
                writer.release()
            except Exception:
                pass
        try:
            src.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
