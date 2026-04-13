#!/usr/bin/env python3
"""
Layer 3 visualizer helpers (derived from Layer 2 features JSON).

This folder previously had the Layer 3 Python logic deleted by request.
This file is intentionally standalone and depends only on:
  - matplotlib
  - numpy
  - json

It consumes the JSON produced by:
  software/layer2_signal_processing/examples/offline_from_captured_frames.py
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")  # headless safe on Jetson
import matplotlib.pyplot as plt
import numpy as np


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def load_layer2_features(path: Path) -> list[dict[str, Any]]:
    with open(path, "r") as f:
        data = json.load(f)

    if isinstance(data, list):
        frames = data
    elif isinstance(data, dict) and isinstance(data.get("features"), list):
        frames = data["features"]
    else:
        raise RuntimeError("Expected list input or a top-level {'features':[...]} object.")

    return frames


def _sorted_by_frame_number(frames: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(x: dict[str, Any]) -> int:
        try:
            return int(x.get("frame_number"))
        except Exception:
            return 0

    return sorted(list(frames), key=key)


@dataclass(frozen=True, slots=True)
class Layer3Feature:
    frame_number: int
    timestamp_ms: float
    vector: list[float]


def derive_layer3_features(frames: list[dict[str, Any]]) -> list[Layer3Feature]:
    derived: list[Layer3Feature] = []
    for fr in frames:
        frame_number = int(fr["frame_number"])
        timestamp_ms = float(fr["timestamp_ms"])
        vec = fr.get("vector", [])
        if not isinstance(vec, list):
            vec = list(vec)
        derived.append(
            Layer3Feature(
                frame_number=frame_number,
                timestamp_ms=timestamp_ms,
                vector=[float(x) for x in vec],
            )
        )
    return derived


def save_layer3_features_json(out_path: Path, input_path: Path, derived: list[Layer3Feature]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "input": str(input_path),
        "frames": [
            {"frame_number": d.frame_number, "timestamp_ms": d.timestamp_ms, "vector": d.vector}
            for d in derived
        ],
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)


def plot_vector_trend(out_path: Path, frames: list[dict[str, Any]], dpi: int = 150) -> None:
    vectors = []
    for fr in frames:
        vec = fr.get("vector", [])
        vectors.append([float(x) for x in vec])

    if not vectors or not vectors[0]:
        raise RuntimeError("No 'vector' data found in frames.")

    dim = len(vectors[0])
    arr = np.asarray(vectors, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[1] != dim:
        raise RuntimeError(f"Inconsistent vector dimensions: got shape {arr.shape}.")

    x = np.arange(len(frames), dtype=np.int32)
    fig, ax = plt.subplots(figsize=(10, 5))
    for d in range(dim):
        ax.plot(x, arr[:, d], linewidth=1.2, label=f"v{d}")
    ax.set_title("Layer 2 vector trend (derived Layer 3 vector)")
    ax.set_xlabel("Frame index (sorted)")
    ax.set_ylabel("Vector value")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)


def plot_frame_heatmaps(
    out_path: Path,
    frame: dict[str, Any],
    dpi: int = 150,
) -> None:
    range_hm = frame.get("range_heatmap", [])
    doppler_hm = frame.get("doppler_heatmap", [])
    vector = frame.get("vector", [])
    point_count = frame.get("point_count", None)

    range_arr = np.asarray(range_hm, dtype=np.float32).reshape(-1)
    doppler_arr = np.asarray(doppler_hm, dtype=np.float32).reshape(-1)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    ax0, ax1 = axes

    ax0.bar(np.arange(range_arr.size), range_arr, width=0.9, color="#1f77b4", alpha=0.85)
    ax0.set_title("Range heatmap")
    ax0.set_xlabel("Range bin")
    ax0.set_ylabel("Value")
    ax0.grid(True, axis="y", alpha=0.25)

    ax1.bar(np.arange(doppler_arr.size), doppler_arr, width=0.9, color="#ff7f0e", alpha=0.85)
    ax1.set_title("Doppler heatmap")
    ax1.set_xlabel("Doppler bin")
    ax1.grid(True, axis="y", alpha=0.25)

    frame_number = frame.get("frame_number", "n/a")
    timestamp_ms = frame.get("timestamp_ms", "n/a")
    vec_short = None
    try:
        vec_short = [round(float(x), 3) for x in vector]
    except Exception:
        vec_short = None

    title = f"Frame {frame_number} | t_ms={timestamp_ms}"
    if vec_short is not None:
        title += f" | vector={vec_short}"
    if point_count is not None:
        try:
            title += f" | points={int(point_count)}"
        except Exception:
            pass

    fig.suptitle(title, fontsize=11)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)


def choose_plot_indices(n_frames: int, count: int) -> list[int]:
    if n_frames <= 0 or count <= 0:
        return []
    if count >= n_frames:
        return list(range(n_frames))
    if count == 1:
        return [0]
    idx = np.linspace(0, n_frames - 1, num=count, dtype=int).tolist()
    # Deduplicate while preserving order.
    out: list[int] = []
    seen: set[int] = set()
    for i in idx:
        if i not in seen:
            out.append(i)
            seen.add(i)
    return out


def safe_frame_filename_token(value: Any) -> str:
    s = str(value)
    return s.replace("/", "_")


def run_visualization(
    *,
    input_path: Path,
    outdir: Path,
    max_frames: int = 0,
    plot_frames: int = 6,
    vector_trend: bool = True,
    write_layer3_json: bool = True,
    verbose: bool = False,
) -> dict[str, Any]:
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    start = time.time()
    frames = _sorted_by_frame_number(load_layer2_features(input_path))
    if not frames:
        raise RuntimeError("No frames found in input JSON.")

    if max_frames and max_frames > 0:
        frames = frames[:max_frames]

    outdir.mkdir(parents=True, exist_ok=True)
    logger.info("Loaded %d frames", len(frames))

    derived = derive_layer3_features(frames)

    if write_layer3_json:
        save_layer3_features_json(outdir / "layer3_features.json", input_path, derived)
        logger.info("Wrote: %s", outdir / "layer3_features.json")

    if vector_trend:
        plot_vector_trend(outdir / "vector_trend.png", frames)
        logger.info("Wrote: %s", outdir / "vector_trend.png")

    indices = choose_plot_indices(len(frames), plot_frames)
    logger.info("Saving heatmaps for %d frame(s)...", len(indices))
    for idx in indices:
        fr = frames[idx]
        token = safe_frame_filename_token(fr.get("frame_number", idx))
        plot_frame_heatmaps(outdir / f"frame_{token}_heatmaps.png", fr)

    result = {"frames_processed": len(frames), "duration_seconds": time.time() - start, "outdir": str(outdir)}
    return result

