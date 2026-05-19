"""CLI helper to normalize an mmWave capture JSON file."""

from __future__ import annotations

import argparse
from pathlib import Path

from .normalized import dump_normalized_mmwave_frames, load_normalized_mmwave_frames
from .visualization import render_top_down_jpeg


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize mmWave frames and optionally render a top-down preview")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--preview", default="")
    parser.add_argument("--radar-id", default="radar_main")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    frames = load_normalized_mmwave_frames(args.input, radar_id=args.radar_id)
    dump_normalized_mmwave_frames(frames, args.output)
    if args.preview and frames:
        render_top_down_jpeg(frames[-1], Path(args.preview))
    print(f"frames={len(frames)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
