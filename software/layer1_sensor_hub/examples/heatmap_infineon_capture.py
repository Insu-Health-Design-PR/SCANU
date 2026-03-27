"""
Record thermal heatmap + Infineon LTR11 panel side-by-side (no mmWave).

Useful when you only need thermal + 60 GHz presence without TI UART traffic.

Example:
  python3 heatmap_infineon_capture.py \\
    --frames 300 --video out.mp4 --thermal-device 0
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

from layer1_radar import ThermalCameraSource


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Thermal heatmap + Infineon panel → MP4")
    parser.add_argument("--frames", "-n", type=int, default=300, help="Frame count")
    parser.add_argument("--fps", type=float, default=10.0, help="Output video FPS")
    parser.add_argument("--video", default="heatmap_infineon.mp4", help="Output MP4")
    parser.add_argument("--output", "-o", default=None, help="Optional JSON lines / list dump")
    parser.add_argument("--panel-w", type=int, default=640, help="Width per panel (thermal | Infineon)")
    parser.add_argument("--panel-h", type=int, default=480, help="Height per panel")
    parser.add_argument("--thermal-device", type=int, default=0)
    parser.add_argument("--thermal-width", type=int, default=640)
    parser.add_argument("--thermal-height", type=int, default=480)
    parser.add_argument("--thermal-fps", type=int, default=30)
    parser.add_argument("--infineon-uuid", default=None)
    parser.add_argument("--no-infineon", action="store_true", help="Thermal heatmap only (right panel blank)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    W, H = int(args.panel_w), int(args.panel_h)
    hist_len = max(int(args.fps * 30), 30)
    inf_presence_hist: deque[float] = deque(maxlen=hist_len)
    inf_motion_hist: deque[float] = deque(maxlen=hist_len)

    try:
        thermal = ThermalCameraSource(
            device=args.thermal_device,
            width=args.thermal_width,
            height=args.thermal_height,
            fps=args.thermal_fps,
        )
    except Exception as exc:
        print(f"ERROR: thermal camera: {exc}")
        sys.exit(1)

    inf_provider = None
    if not args.no_infineon:
        try:
            from software.layer1_radar.infineon import IfxLtr11PresenceProvider

            inf_provider = IfxLtr11PresenceProvider(uuid=args.infineon_uuid)
            print("Infineon LTR11 enabled")
        except Exception as exc:
            print(f"[warn] Infineon disabled: {exc}")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(args.video, fourcc, float(args.fps), (W * 2, H))
    if not writer.isOpened():
        thermal.close()
        print(f"ERROR: could not open video writer: {args.video}")
        sys.exit(1)

    frames_out: list[dict] = []
    t0 = time.time()

    try:
        for i in range(args.frames):
            heat = thermal.read_colormap_bgr()
            if heat is None:
                heat = np.zeros((H, W, 3), dtype=np.uint8)
            else:
                heat = cv2.resize(heat, (W, H), interpolation=cv2.INTER_LINEAR)

            cv2.putText(
                heat,
                "Thermal (heatmap)",
                (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
            )

            inf_sample = None
            if inf_provider is not None:
                try:
                    presence_raw, motion_raw, _d = inf_provider.read_sample()
                    inf_presence_hist.append(float(presence_raw))
                    inf_motion_hist.append(float(motion_raw))
                    meta = getattr(inf_provider, "last_meta", None)
                    inf_sample = {
                        "presence_raw": float(presence_raw),
                        "motion_raw": float(motion_raw),
                        "meta": meta,
                    }
                except Exception as exc:
                    logger.debug("Infineon read failed: %s", exc)

            inf_bgr = render_infineon_panel(W, H, inf_presence_hist, inf_motion_hist)
            combined = np.hstack((heat, inf_bgr))
            writer.write(combined)

            if args.output:
                gray = cv2.cvtColor(heat, cv2.COLOR_BGR2GRAY)
                frames_out.append(
                    {
                        "index": i,
                        "thermal_mean_u8": float(np.mean(gray)) if gray.size else 0.0,
                        "infineon": inf_sample,
                    }
                )

            elapsed = time.time() - t0
            fps_live = (i + 1) / elapsed if elapsed > 0 else 0.0
            print(f"\rFrame {i + 1}/{args.frames} | FPS: {fps_live:.1f}", end="")

        print(f"\nSaved: {args.video}")
        if args.output:
            with open(args.output, "w") as f:
                json.dump(frames_out, f, indent=2)
            print(f"JSON: {args.output}")

    finally:
        writer.release()
        thermal.close()
        if inf_provider is not None:
            try:
                inf_provider.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
