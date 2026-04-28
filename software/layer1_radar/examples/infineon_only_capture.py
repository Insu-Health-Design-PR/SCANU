#!/usr/bin/env python3
"""
Infineon LTR11 presence panel only → MP4 (no mmWave, no thermal).

Example:
  python3 infineon_only_capture.py --frames 300 --video infineon_out.mp4
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

_repo_root = Path(__file__).resolve().parents[3]
_software_root = _repo_root / "software"
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_software_root))


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def render_infineon_panel(
    width: int,
    height: int,
    presence_hist: deque[float],
    motion_hist: deque[float],
) -> np.ndarray:
    panel = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.putText(
        panel,
        "Infineon (LTR11)",
        (10, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )
    if len(presence_hist) == 0:
        cv2.putText(
            panel,
            "No data",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (200, 200, 200),
            2,
        )
        return panel

    p = np.asarray(presence_hist, dtype=np.float32)
    m = np.asarray(motion_hist, dtype=np.float32) if len(motion_hist) == len(presence_hist) else None
    p_max = float(np.percentile(p, 98)) if p.size >= 5 else float(np.max(p))
    p_max = max(p_max, 1e-6)
    p_norm = np.clip(p / p_max, 0.0, 1.0)

    left, right, top, bottom = 10, width - 10, 80, height - 20
    cv2.rectangle(panel, (left, top), (right, bottom), (60, 60, 60), 1)
    n = p_norm.size
    xs = np.linspace(left, right, n, dtype=np.int32)
    ys = (bottom - (p_norm * (bottom - top))).astype(np.int32)
    pts = np.column_stack([xs, ys]).reshape((-1, 1, 2))
    cv2.polylines(panel, [pts], isClosed=False, color=(0, 200, 255), thickness=2)

    cur_presence = float(p[-1])
    cur_motion = float(m[-1]) if m is not None and m.size > 0 else 0.0
    cv2.putText(
        panel,
        f"motion_energy: {cur_presence:.6f}",
        (10, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
    )
    motion_color = (0, 255, 0) if cur_motion >= 0.5 else (80, 80, 80)
    cv2.circle(panel, (right - 20, 52), 10, motion_color, -1)
    cv2.putText(
        panel,
        "motion",
        (right - 95, 56),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (220, 220, 220),
        2,
    )
    return panel


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
    parser = argparse.ArgumentParser(description="Infineon LTR11 panel only → MP4")
    parser.add_argument("--frames", "-n", type=int, default=300)
    parser.add_argument("--fps", type=float, default=10.0)
    parser.add_argument("--video", "-v", default="infineon_only.mp4")
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--panel-w", type=int, default=640)
    parser.add_argument("--panel-h", type=int, default=480)
    parser.add_argument("--infineon-uuid", default=None)
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
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

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    W, H = int(args.panel_w), int(args.panel_h)
    hist_len = max(int(args.fps * 30), 30)
    presence_hist: deque[float] = deque(maxlen=hist_len)
    motion_hist: deque[float] = deque(maxlen=hist_len)

    try:
        from software.layer1_radar.infineon import IfxLtr11PresenceProvider

        provider = IfxLtr11PresenceProvider(uuid=args.infineon_uuid)
        print("Infineon LTR11 enabled")
    except Exception as exc:
        print(f"ERROR: Infineon: {exc}")
        sys.exit(1)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(args.video, fourcc, float(args.fps), (W, H))
    if not writer.isOpened():
        try:
            provider.close()
        except Exception:
            pass
        print(f"ERROR: could not open video writer: {args.video}")
        sys.exit(1)

    frames_out: list[dict] = []
    t0 = time.time()
    wrote_ok = False

    try:
        for i in range(args.frames):
            sample = None
            try:
                presence_raw, motion_raw, _d = provider.read_sample()
                presence_hist.append(float(presence_raw))
                motion_hist.append(float(motion_raw))
                sample = {
                    "presence_raw": float(presence_raw),
                    "motion_raw": float(motion_raw),
                    "meta": getattr(provider, "last_meta", None),
                }
            except Exception as exc:
                logger.debug("read_sample: %s", exc)

            panel = render_infineon_panel(W, H, presence_hist, motion_hist)
            _write_live_frame(args.live_frame, panel)
            writer.write(panel)
            if args.output:
                frames_out.append({"index": i, "infineon": sample})

            dt = time.time() - t0
            fps_live = (i + 1) / dt if dt > 0 else 0.0
            print(f"\rFrame {i + 1}/{args.frames} | FPS: {fps_live:.1f}", end="")

        print(f"\nSaved: {args.video}")
        if args.output:
            with open(args.output, "w") as f:
                json.dump(frames_out, f, indent=2)
            print(f"JSON: {args.output}")
        wrote_ok = True
    finally:
        writer.release()
        try:
            provider.close()
        except Exception:
            pass

    if wrote_ok and not args.no_reencode:
        from mp4_web_preview import reencode_mp4_for_web

        reencode_mp4_for_web(args.video)


if __name__ == "__main__":
    main()
