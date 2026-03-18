"""Run the live sensor through Layer 1 and Layer 2 and print Layer 2 outputs."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add software directory to import path.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from layer2_signal_processing.live_pipeline import Layer1RealtimePipeline


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def _to_serializable(packet: Any) -> dict[str, Any]:
    processed = packet.processed
    features = packet.features
    return {
        "ProcessedFrame": {
            "frame_number": processed.frame_number,
            "timestamp_ms": processed.timestamp_ms,
            "source_timestamp_cycles": processed.source_timestamp_cycles,
            "range_doppler": processed.range_doppler.tolist(),
            "point_cloud": processed.point_cloud.tolist(),
        },
        "HeatmapFeatures": {
            "frame_number": features.frame_number,
            "timestamp_ms": features.timestamp_ms,
            "range_heatmap": features.range_heatmap.tolist(),
            "doppler_heatmap": features.doppler_heatmap.tolist(),
            "vector": features.vector.tolist(),
        },
    }


def _print_summary(packet: Any, fps: float) -> None:
    vector = [round(float(v), 2) for v in packet.features.vector.tolist()]
    print(
        f"\rFrame {packet.processed.frame_number:4d} | "
        f"rd={packet.processed.range_doppler.shape} | "
        f"pc={packet.processed.point_cloud.shape} | "
        f"vec={vector} | {fps:.1f} FPS",
        end="",
    )


def _print_full(packet: Any, fps: float) -> None:
    payload = _to_serializable(packet)
    print(f"\n\n=== Frame {packet.processed.frame_number} | {fps:.1f} FPS ===")
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run live sensor data through Layer 1 and Layer 2 and print Layer 2 output",
    )
    parser.add_argument("--frames", "-n", type=int, default=20, help="Maximum frames to process")
    parser.add_argument("--config", "-c", type=str, default=None, help="Optional radar config file")
    parser.add_argument("--config-port", type=str, default=None, help="Manual config port override")
    parser.add_argument("--data-port", type=str, default=None, help="Manual data port override")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print full ProcessedFrame and HeatmapFeatures JSON for every frame",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    pipeline = Layer1RealtimePipeline()
    start_time = time.time()
    processed_count = 0

    try:
        print("\n" + "=" * 72)
        print("LIVE SENSOR -> LAYER 1 -> LAYER 2")
        print("=" * 72)

        print("\n[1/3] Connecting and configuring radar...")
        pipeline.connect_and_configure(
            config_port=args.config_port,
            data_port=args.data_port,
            config_path=args.config,
        )
        print("      Radar connected and configured")

        print(f"\n[2/3] Processing up to {args.frames} frame(s)...")
        if args.full:
            print("      Full Layer 2 output enabled\n")
        else:
            print("      Summary output enabled\n")

        for packet in pipeline.stream(max_frames=args.frames):
            processed_count += 1
            elapsed = time.time() - start_time
            fps = processed_count / elapsed if elapsed > 0 else 0.0
            if args.full:
                _print_full(packet, fps)
            else:
                _print_summary(packet, fps)

        if not args.full:
            print()

        print("\n[3/3] Complete")
        print(f"      Processed frames: {processed_count}")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        pipeline.close()
        print("      Pipeline closed")


if __name__ == "__main__":
    main()
