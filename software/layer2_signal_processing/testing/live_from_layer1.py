"""Example: stream live Layer 1 radar data into Layer 2 processing."""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import sys

# Add project root to import path so ``software.*`` imports work from zip extracts.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from software.layer2_signal_processing.live_pipeline import Layer1RealtimePipeline


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream live Layer 1 radar data into Layer 2")
    parser.add_argument("--frames", "-n", type=int, default=100, help="Maximum frames to process")
    parser.add_argument("--config", "-c", type=str, default=None, help="Optional radar config file")
    parser.add_argument("--config-port", type=str, default=None, help="Manual config port override")
    parser.add_argument("--data-port", type=str, default=None, help="Manual data port override")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    setup_logging(args.verbose)

    pipeline = Layer1RealtimePipeline()
    start_time = time.time()

    try:
        print("\n" + "=" * 64)
        print("LIVE PIPELINE: Layer 1 -> Layer 2")
        print("=" * 64)

        print("\n[1/3] Connecting and configuring radar...")
        pipeline.connect_and_configure(
            config_port=args.config_port,
            data_port=args.data_port,
            config_path=args.config,
        )
        print("      Radar connected and configured")

        print(f"\n[2/3] Streaming up to {args.frames} frames...")
        print("      Press Ctrl+C to stop early\n")

        processed_count = 0
        for packet in pipeline.stream(max_frames=args.frames):
            processed_count += 1
            elapsed = time.time() - start_time
            fps = processed_count / elapsed if elapsed > 0 else 0.0
            vector = [round(float(v), 2) for v in packet.features.vector.tolist()]

            print(
                f"\r      Frame {packet.processed.frame_number:4d}: "
                f"rd={packet.processed.range_doppler.shape} "
                f"pc={packet.processed.point_cloud.shape} "
                f"vec={vector} "
                f"{fps:.1f} FPS",
                end="",
            )

        print("\n\n[3/3] Stream complete")
        print(f"      Processed frames: {processed_count}")

    except KeyboardInterrupt:
        print("\n\nStream interrupted by user")
    finally:
        pipeline.close()
        print("      Pipeline closed")


if __name__ == "__main__":
    main()
