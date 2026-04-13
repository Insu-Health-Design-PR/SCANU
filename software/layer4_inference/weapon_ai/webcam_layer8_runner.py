#!/usr/bin/env python3
"""
Layer 8 entrypoint: live webcam + weapon_ai.infer_thermal_objects (YOLO + p(gun) head).

Run with cwd = layer4_inference/ (see layer8_ui.sensor_runner).

  python weapon_ai/webcam_layer8_runner.py \\
    --checkpoint ../trained_models/gun_detection/gun_prob_best.pt \\
    --webcam-device 0 \\
    --live-frame /abs/path/live_webcam.jpg \\
    --video /abs/path/out.mp4
"""

from __future__ import annotations

import argparse
import shlex
import sys


def main() -> None:
    p = argparse.ArgumentParser(description="Webcam live infer for Layer 8 UI.")
    p.add_argument("--webcam-device", type=int, default=0)
    p.add_argument(
        "--checkpoint",
        type=str,
        required=True,
        help="Path to .pt checkpoint (gun_prob BCE or safe/unsafe).",
    )
    p.add_argument(
        "--live-frame",
        type=str,
        required=True,
        help="JPEG path updated every frame (MJPEG source for UI).",
    )
    p.add_argument(
        "--video",
        type=str,
        default="",
        help="Optional annotated MP4 output (same as infer --output).",
    )
    p.add_argument(
        "--frames",
        type=int,
        default=0,
        help="Max frames (0 = until process stopped / stream ends).",
    )
    p.add_argument(
        "--weapon-extra-args",
        type=str,
        default="",
        help="Extra arguments forwarded to infer_thermal_objects (quoted shell string).",
    )
    args = p.parse_args()

    forward: list[str] = [
        "infer_thermal_objects",
        "--checkpoint",
        args.checkpoint,
        "--source",
        str(int(args.webcam_device)),
        "--no_imshow",
        "--live_jpg",
        args.live_frame,
    ]
    if args.video.strip():
        forward.extend(["--output", args.video.strip()])
    if int(args.frames) > 0:
        forward.extend(["--max_frames", str(int(args.frames))])
    extra = args.weapon_extra_args.strip()
    if extra:
        forward.extend(shlex.split(extra))

    sys.argv = forward
    from weapon_ai import infer_thermal_objects

    infer_thermal_objects.main()


if __name__ == "__main__":
    main()
