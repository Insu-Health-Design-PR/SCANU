"""Run the live sensor through Layer 1 and Layer 2 and print Layer 2 outputs."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to import path so ``software.*`` imports work from zip extracts.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run live sensor data through Layer 1 and Layer 2 and print Layer 2 output.",
    )
    parser.add_argument("--frames", "-n", type=int, default=20, help="Maximum frames to process")
    parser.add_argument("--config", "-c", type=str, default=None, help="Optional radar config file")
    parser.add_argument(
        "--config-port",
        "--cli-port",
        dest="config_port",
        type=str,
        default=None,
        help="Manual config/CLI port override",
    )
    parser.add_argument("--data-port", type=str, default=None, help="Manual data port override")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print full ProcessedFrame and HeatmapFeatures JSON for every frame",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate arguments, print the runtime plan, and exit without starting the sensor",
    )
    return parser


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.frames <= 0:
        parser.error("--frames must be greater than 0")

    if args.config is not None and not Path(args.config).is_file():
        parser.error(f"--config file does not exist: {args.config}")

    has_config_port = bool(args.config_port)
    has_data_port = bool(args.data_port)
    if has_config_port != has_data_port:
        parser.error(
            "manual port mode requires both --config-port/--cli-port and --data-port"
        )


def _print_header() -> None:
    print("\n" + "=" * 72)
    print("LIVE SENSOR -> LAYER 1 -> LAYER 2")
    print("=" * 72)


def _print_runtime_plan(args: argparse.Namespace) -> None:
    port_mode = "manual" if args.config_port and args.data_port else "autodetect"
    config_source = args.config if args.config else "default"
    output_mode = "full JSON" if args.full else "summary"

    print("\nRuntime plan")
    print("-" * 72)
    print(f"port mode: {port_mode}")
    print(f"config port: {args.config_port or 'autodetect at runtime'}")
    print(f"data port: {args.data_port or 'autodetect at runtime'}")
    print(f"config source: {config_source}")
    print(f"frames: {args.frames}")
    print(f"output mode: {output_mode}")
    print(f"verbose logging: {'yes' if args.verbose else 'no'}")


def _print_error_with_tips(exc: Exception) -> None:
    print("\nRuntime error: failed to run the live Layer 1 -> Layer 2 pipeline.", file=sys.stderr)
    print(str(exc), file=sys.stderr)
    print("\nTips:", file=sys.stderr)
    print("  - Verify the radar is visible in Linux with: ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null", file=sys.stderr)
    print("  - Verify config/data port are not inverted", file=sys.stderr)
    print("  - Re-run with -v for more detailed logs", file=sys.stderr)


def _default_pipeline_factory() -> Any:
    from software.layer2_signal_processing.live_pipeline import Layer1RealtimePipeline

    return Layer1RealtimePipeline()


def main(
    argv: list[str] | None = None,
    pipeline_factory: Any | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)

    setup_logging(args.verbose)

    try:
        _print_header()
        _print_runtime_plan(args)

        if args.check:
            print("\nCheck mode enabled: validation complete, sensor was not started.")
            return 0

        pipeline_builder = pipeline_factory or _default_pipeline_factory
        pipeline = pipeline_builder()
        start_time = time.time()
        processed_count = 0

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
        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as exc:
        _print_error_with_tips(exc)
        return 1
    finally:
        pipeline = locals().get("pipeline")
        if pipeline is not None:
            pipeline.close()
            print("      Pipeline closed")


if __name__ == "__main__":
    raise SystemExit(main())
