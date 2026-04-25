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
import importlib
import importlib.util
import shlex
import sys
from pathlib import Path


def _infer_main_callable():
    """
    Load ``infer_thermal_objects.main`` from the sibling file.

    Avoids ``from weapon_ai import infer_thermal_objects`` (not re-exported in ``weapon_ai``)
    and avoids a wrong ``weapon_ai`` on ``PYTHONPATH`` shadowing this package.
    """
    importlib.import_module("weapon_ai")  # ensure package metadata / __path__

    path = Path(__file__).resolve().parent / "infer_thermal_objects.py"
    if not path.is_file():
        raise FileNotFoundError(path)
    name = "weapon_ai.infer_thermal_objects"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load spec for {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod.main


def main() -> None:
    p = argparse.ArgumentParser(description="Webcam live infer for Layer 8 UI.", allow_abbrev=False)
    p.add_argument("--webcam-device", type=str, default="0")
    p.add_argument("--capture-width", type=int, default=1920)
    p.add_argument("--capture-height", type=int, default=1080)
    p.add_argument(
        "--checkpoint",
        type=str,
        required=True,
        help="Path to .pt checkpoint (gun_prob BCE or safe/unsafe).",
    )
    p.add_argument(
        "--live-frame",
        type=str,
        default="",
        help="Optional JPEG path updated every frame (legacy MJPEG source for UI).",
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
        "--metrics-json",
        type=str,
        default="",
        help="Optional JSON path for Layer 8 dashboard threat metrics.",
    )
    p.add_argument(
        "--live-ipc-frame",
        type=str,
        default="",
        help="Optional mmap latest-frame path for dashboard low-latency preview.",
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
        str(args.webcam_device).strip(),
        "--capture_width",
        str(int(args.capture_width)),
        "--capture_height",
        str(int(args.capture_height)),
        "--no_imshow",
    ]
    if args.live_frame.strip():
        forward.extend(["--live_jpg", args.live_frame.strip()])
    if args.video.strip():
        forward.extend(["--output", args.video.strip()])
    if int(args.frames) > 0:
        forward.extend(["--max_frames", str(int(args.frames))])
    if args.metrics_json.strip():
        forward.extend(["--live_metrics_json", args.metrics_json.strip()])
    if args.live_ipc_frame.strip():
        forward.extend(["--live_ipc_frame", args.live_ipc_frame.strip()])
    extra = args.weapon_extra_args.strip()
    if extra:
        forward.extend(shlex.split(extra))

    sys.argv = forward
    infer_main = _infer_main_callable()
    infer_main()


if __name__ == "__main__":
    main()
