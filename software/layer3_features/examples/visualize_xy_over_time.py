#!/usr/bin/env python3
"""
Visualize x/y trajectory over time from Layer1-style radar capture JSON.

This consumes JSON produced by:
  software/layer1_radar/examples/capture_frames.py

It then estimates a single "target" point per frame (by max SNR or top-k
average), and plots:
  - x vs time
  - y vs time
  - x-y scatter colored by time
  - x-y occupancy heatmap

Outputs are written under:
  software/layer3_features/xy_viz/<input_stem>/
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import numpy as np


# Add project root to import path so `software.*` imports work locally.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def _load_capture_json(path: Path) -> tuple[list[dict[str, Any]], float | None]:
    with open(path, "r") as f:
        payload = json.load(f)

    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise RuntimeError(f"Invalid capture file (missing/empty 'frames'): {path}")

    capture_info = payload.get("capture_info", {})
    fps = None
    if isinstance(capture_info, dict) and "fps" in capture_info:
        try:
            fps = float(capture_info["fps"])
        except Exception:
            fps = None

    return frames, fps


def _choose_target_xy(
    frame: dict[str, Any],
    *,
    top_k: int,
    snr_threshold: float,
) -> tuple[float, float] | None:
    points = frame.get("points", [])
    if not isinstance(points, list) or not points:
        return None

    scored: list[tuple[float, float, float]] = []  # (snr, x, y)
    for p in points:
        if not isinstance(p, dict):
            continue
        snr = float(p.get("snr", 0.0) or 0.0)
        if snr < snr_threshold:
            continue
        x = float(p.get("x", 0.0) or 0.0)
        y = float(p.get("y", 0.0) or 0.0)
        scored.append((snr, x, y))

    if not scored:
        return None

    scored.sort(key=lambda t: t[0], reverse=True)
    k = max(1, min(int(top_k), len(scored)))
    top = scored[:k]
    xs = [t[1] for t in top]
    ys = [t[2] for t in top]
    return float(np.mean(xs)), float(np.mean(ys))


def _limit_frames_by_seconds(
    frames: list[dict[str, Any]],
    fps: float | None,
    max_seconds: float,
) -> list[dict[str, Any]]:
    if max_seconds is None or max_seconds <= 0:
        return frames
    if fps is None or fps <= 0:
        # Fallback: assume 10 FPS if capture_info is missing.
        fps = 10.0
    max_frames = int(math.floor(max_seconds * fps))
    return frames[: max_frames if max_frames > 0 else len(frames)]


@dataclass(frozen=True, slots=True)
class Trajectory:
    t_s: np.ndarray
    x_m: np.ndarray
    y_m: np.ndarray


def extract_xy_trajectory(
    frames: list[dict[str, Any]],
    fps: float | None,
    *,
    max_seconds: float,
    top_k: int,
    snr_threshold: float,
) -> Trajectory:
    limited = _limit_frames_by_seconds(frames, fps, max_seconds)
    if fps is None or fps <= 0:
        fps = 10.0

    xs: list[float] = []
    ys: list[float] = []
    ts: list[float] = []

    for i, frame in enumerate(limited):
        target = _choose_target_xy(frame, top_k=top_k, snr_threshold=snr_threshold)
        if target is None:
            continue
        x, y = target
        xs.append(x)
        ys.append(y)
        ts.append(i / fps)

    if not xs:
        raise RuntimeError("No valid points for trajectory (check snr_threshold/top_k).")

    return Trajectory(
        t_s=np.asarray(ts, dtype=np.float32),
        x_m=np.asarray(xs, dtype=np.float32),
        y_m=np.asarray(ys, dtype=np.float32),
    )


def plot_xy_time_series(
    outdir: Path,
    traj: Trajectory,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(traj.t_s, traj.x_m, linewidth=1.5)
    ax.set_title("Target X over time")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("X (m)")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "x_over_time.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(traj.t_s, traj.y_m, linewidth=1.5)
    ax.set_title("Target Y over time")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Y (m)")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "y_over_time.png", dpi=150)
    plt.close(fig)


def plot_xy_map(
    outdir: Path,
    traj: Trajectory,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    # Scatter map colored by time.
    fig, ax = plt.subplots(figsize=(7.5, 6))
    sc = ax.scatter(traj.x_m, traj.y_m, c=traj.t_s, cmap="viridis", s=18, alpha=0.95)
    ax.plot(traj.x_m, traj.y_m, linewidth=1.0, alpha=0.35, color="white")
    ax.set_title("Target position map (x-y) colored by time")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.grid(True, alpha=0.2)
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("Time (s)")
    fig.tight_layout()
    fig.savefig(outdir / "xy_map_time_scatter.png", dpi=150)
    plt.close(fig)

    # Occupancy heatmap (2D histogram weighted by equal time sample).
    x = traj.x_m
    y = traj.y_m
    # Auto binning but keep it reasonable.
    bins = 64
    x_bins = np.linspace(float(np.min(x)), float(np.max(x)), bins)
    y_bins = np.linspace(float(np.min(y)), float(np.max(y)), bins)
    hist, x_edges, y_edges = np.histogram2d(x, y, bins=[x_bins, y_bins])

    fig, ax = plt.subplots(figsize=(7.5, 6))
    im = ax.imshow(
        hist.T,
        origin="lower",
        extent=[x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]],
        aspect="auto",
        cmap="magma",
    )
    ax.set_title("Target occupancy heatmap (x-y)")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    fig.colorbar(im, ax=ax, label="Counts")
    fig.tight_layout()
    fig.savefig(outdir / "xy_occupancy_heatmap.png", dpi=150)
    plt.close(fig)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Visualize x/y trajectory over time from radar capture JSON")
    p.add_argument(
        "--inputs",
        "-i",
        nargs="+",
        required=True,
        help="One or more JSON capture files (moving_person_frames.json, empty_frames.json, etc.)",
    )
    p.add_argument("--max-seconds", "-t", type=float, default=30.0, help="Max time window to plot (seconds)")
    p.add_argument("--top-k", type=int, default=1, help="Average of top-k points by SNR per frame")
    p.add_argument("--snr-threshold", type=float, default=0.0, help="Ignore points with snr < threshold")
    p.add_argument("--outdir", type=str, default=None, help="Output root (default: software/layer3_features/xy_viz)")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(bool(args.verbose))
    logger = logging.getLogger(__name__)

    out_root = Path(args.outdir) if args.outdir is not None else Path(__file__).resolve().parents[1] / "xy_viz"
    out_root.mkdir(parents=True, exist_ok=True)

    for input_str in args.inputs:
        input_path = Path(input_str)
        if not input_path.is_file():
            raise SystemExit(f"--inputs file not found: {input_path}")

        frames, fps = _load_capture_json(input_path)
        logger.info("Loaded %d frames from %s (fps=%s)", len(frames), input_path.name, str(fps))

        traj = extract_xy_trajectory(
            frames,
            fps,
            max_seconds=float(args.max_seconds),
            top_k=int(args.top_k),
            snr_threshold=float(args.snr_threshold),
        )

        dataset_out = out_root / input_path.stem
        plot_xy_time_series(dataset_out, traj)
        plot_xy_map(dataset_out, traj)
        logger.info("Wrote plots to: %s", str(dataset_out))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

