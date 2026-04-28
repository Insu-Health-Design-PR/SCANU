#!/usr/bin/env python3
"""
Visualize Layer 2 features JSON and derive Layer 3 vector features.

This is an offline visualization helper:
  input:  software/layer2_signal_processing/examples/offline_from_captured_frames.py output
  output: PNG heatmaps + vector trend, and optionally layer3_features.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to import path so `software.*` imports work locally.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from software.layer3_features.visualizer import run_visualization


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Visualize layer2_features.json as Layer 3 features")
    p.add_argument("--input", "-i", required=True, help="Path to layer2_features.json")
    p.add_argument("--outdir", "-o", default=None, help="Output directory (default: alongside input)")
    p.add_argument("--max-frames", "-n", type=int, default=0, help="Max frames to process (0 = all)")
    p.add_argument("--plot-frames", type=int, default=6, help="How many frames to save heatmaps for")
    p.add_argument("--no-vector-trend", action="store_true", help="Skip vector trend plot")
    p.add_argument(
        "--no-layer3-json",
        action="store_true",
        help="Skip writing derived layer3_features.json",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    if not input_path.is_file():
        raise SystemExit(f"--input does not exist: {input_path}")

    if args.outdir is not None:
        outdir = Path(args.outdir)
    else:
        # Default to the layer3 folder (not next to the layer2 input file).
        # Create a subfolder per input file stem to avoid overwriting.
        layer3_root = Path(__file__).resolve().parents[1]
        outdir = layer3_root / "layer3_viz" / input_path.stem

    run_visualization(
        input_path=input_path,
        outdir=outdir,
        max_frames=int(args.max_frames),
        plot_frames=int(args.plot_frames),
        vector_trend=not bool(args.no_vector_trend),
        write_layer3_json=not bool(args.no_layer3_json),
        verbose=bool(args.verbose),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

