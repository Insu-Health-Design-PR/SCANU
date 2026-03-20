"""Live smoke-test runner for the Infineon BGT60LTR11AIP presence sensor."""

from __future__ import annotations

import argparse

from software.layer1_sensors_unified.radar_presence_60g import (
    BGT60LTR11AIPSerialConfig,
    BGT60LTR11AIPSerialProvider,
    PresenceProcessor,
    PresenceSource,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read live samples from the Infineon BGT60LTR11AIP sensor."
    )
    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help="Serial port path, for example /dev/ttyACM0. If omitted, auto-detect is used.",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=115200,
        help="Serial baudrate for the sensor output.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=20,
        help="Number of valid samples to print before exiting.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    config = BGT60LTR11AIPSerialConfig(
        port=args.port,
        baudrate=args.baudrate,
    )
    provider = BGT60LTR11AIPSerialProvider(config=config)
    source = PresenceSource(provider)
    processor = PresenceProcessor()

    print("Starting BGT60LTR11AIP live read...")
    try:
        for index in range(args.samples):
            frame = source.read_frame()
            features = processor.extract(frame)

            print(f"\nSample {index + 1}/{args.samples}")
            print(f"FRAME: {frame}")
            print(f"FEATURES: {features}")
    finally:
        provider.disconnect()

    print("\nDone.")


if __name__ == "__main__":
    main()
