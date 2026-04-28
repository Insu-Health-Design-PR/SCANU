#!/usr/bin/env python3
"""
Offline Layer 1 capture -> Layer 2 feature generation.

Input:
  A `captured_frames.json` file produced by:
  `software/layer1_radar/examples/capture_frames.py`

Output:
  A compact JSON containing per-frame Layer 2 heatmap features:
  - range_heatmap
  - doppler_heatmap
  - vector

This intentionally does NOT run live radar IO; it only consumes the saved
Layer 1 capture file.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

# Add project root to import path so `software.*` imports work locally.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from software.layer2_signal_processing import FeatureExtractor, SignalProcessor


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert captured_frames.json to Layer 2 features")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Path to captured_frames.json produced by layer1_radar capture script",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        required=True,
        help="Path to write Layer 2 features JSON",
    )
    parser.add_argument(
        "--max-frames",
        "-n",
        type=int,
        default=0,
        help="Maximum frames to process (0 = all)",
    )
    parser.add_argument(
        "--doppler-bins",
        type=int,
        default=16,
        help="Doppler FFT bins used by SignalProcessor (default: 16)",
    )
    parser.add_argument(
        "--cfar-guard",
        type=int,
        default=1,
        help="CFAR guard cells (default: 1)",
    )
    parser.add_argument(
        "--cfar-train",
        type=int,
        default=2,
        help="CFAR training cells (default: 2)",
    )
    parser.add_argument(
        "--cfar-threshold-scale",
        type=float,
        default=1.8,
        help="CFAR threshold scale (default: 1.8)",
    )
    parser.add_argument(
        "--background-alpha",
        type=float,
        default=0.05,
        help="BackgroundModel alpha (EMA rate). Higher = faster adaptation.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args(argv)
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    input_path = Path(args.input)
    if not input_path.is_file():
        parser.error(f"--input does not exist: {input_path}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Loading: %s", input_path)
    with open(input_path, "r") as f:
        payload = json.load(f)

    frames = payload.get("frames", [])
    if not isinstance(frames, list) or not frames:
        raise RuntimeError("Input JSON does not contain a non-empty 'frames' list")

    max_frames = _coerce_int(args.max_frames, 0)
    if max_frames <= 0 or max_frames > len(frames):
        max_frames = len(frames)

    logger.info("Frames to process: %d (of %d)", max_frames, len(frames))

    processor = SignalProcessor(
        doppler_bins=int(args.doppler_bins),
        cfar_guard=int(args.cfar_guard),
        cfar_train=int(args.cfar_train),
        cfar_threshold_scale=float(args.cfar_threshold_scale),
    )
    # BackgroundModel alpha is set via BackgroundModel, but SignalProcessor currently
    # creates it internally. We patch by feeding a preconfigured background model
    # only if SignalProcessor supports it in your version.
    #
    # Best-effort: try to set alpha on the internal model.
    if hasattr(processor, "_background") and hasattr(processor._background, "alpha"):
        processor._background.alpha = float(args.background_alpha)  # type: ignore[attr-defined]

    extractor = FeatureExtractor()

    results: list[dict[str, Any]] = []
    start_time = time.time()

    for i, frame in enumerate(frames[:max_frames], start=1):
        processed = processor.process(frame)
        features = extractor.extract(processed)

        results.append(
            {
                "frame_number": features.frame_number,
                "timestamp_ms": features.timestamp_ms,
                "range_heatmap": features.range_heatmap.tolist(),
                "doppler_heatmap": features.doppler_heatmap.tolist(),
                "vector": features.vector.tolist(),
                "point_count": int(processed.point_cloud.shape[0]),
            }
        )

        if i == 1 or i % 5 == 0 or i == max_frames:
            elapsed = time.time() - start_time
            fps = i / elapsed if elapsed > 0 else 0.0
            logger.info("Processed %d/%d frames (%.1f FPS)", i, max_frames, fps)

    out = {
        "input": {
            "path": str(input_path),
            "total_frames_in_file": len(frames),
            "processed_frames": max_frames,
        },
        "layer2": {
            "doppler_bins": int(args.doppler_bins),
            "cfar_guard": int(args.cfar_guard),
            "cfar_train": int(args.cfar_train),
            "cfar_threshold_scale": float(args.cfar_threshold_scale),
            "background_alpha": float(args.background_alpha),
        },
        "features": results,
        "timing": {
            "duration_seconds": time.time() - start_time,
        },
    }

    logger.info("Writing output: %s", output_path)
    with open(output_path, "w") as f:
        json.dump(out, f)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

