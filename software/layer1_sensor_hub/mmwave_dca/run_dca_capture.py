"""Command-line entrypoint for DCA1000 raw ADC capture on Jetson/Linux."""

from __future__ import annotations

import argparse
from pathlib import Path

from .capture_runner import CapturePlan, run_capture_plan
from .dca1000_udp import Dca1000NetworkConfig
from .radar_cli import RadarCliConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture raw ADC from TI mmWave + DCA1000EVM")
    parser.add_argument("--cli-port", default="", help="Radar CLI/control port, e.g. /dev/ttyUSB0 (auto-detect if empty)")
    parser.add_argument("--config", required=True, help="Radar .cfg file with LVDS enabled")
    parser.add_argument("--dca-config", default="", help="DCA1000 JSON config for native Jetson UDP control")
    parser.add_argument("--output", default="adc_data.bin", help="Output adc_data.bin path")
    parser.add_argument("--duration-s", type=float, default=5.0)
    parser.add_argument("--max-packets", type=int, default=0)
    parser.add_argument("--pc-ip", default="192.168.33.30")
    parser.add_argument("--dca-ip", default="192.168.33.180")
    parser.add_argument("--data-port", type=int, default=4098)
    parser.add_argument("--config-port", type=int, default=4096)
    parser.add_argument("--skip-radar-config", action="store_true")
    parser.add_argument("--configure-dca", action="store_true", help="Configure DCA1000 over UDP from --dca-config")
    parser.add_argument("--start-dca", action="store_true", help="Send DCA1000 start_record before sensorStart")
    parser.add_argument("--stop-dca", action="store_true", help="Send DCA1000 stop_record after capture")
    parser.add_argument("--no-sensor-start", action="store_true")
    parser.add_argument("--keep-running", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.cli_port:
        from .radar_cli import _find_cli_port
        detected = _find_cli_port()
        if detected is None:
            print("error: no radar CLI port found")
            return 1
        print(f"Auto-detected radar CLI port: {detected}", file=__import__("sys").stderr)
        args.cli_port = detected
    plan = CapturePlan(
        radar_cli=RadarCliConfig(port=args.cli_port),
        radar_config_path=Path(args.config),
        output_path=Path(args.output),
        dca_config_path=Path(args.dca_config) if args.dca_config else None,
        network=Dca1000NetworkConfig(
            pc_ip=args.pc_ip,
            dca_ip=args.dca_ip,
            config_port=args.config_port,
            data_port=args.data_port,
        ),
        record_duration_s=args.duration_s,
        max_packets=args.max_packets,
        configure_radar=not args.skip_radar_config,
        configure_dca=args.configure_dca,
        start_dca_recording=args.start_dca,
        stop_dca_recording_after_capture=args.stop_dca,
        start_sensor=not args.no_sensor_start,
        stop_sensor_after_capture=not args.keep_running,
    )
    result = run_capture_plan(plan)
    print(
        f"saved={result.output_path} packets={result.packets} "
        f"bytes={result.payload_bytes} elapsed_s={result.elapsed_s:.2f} timed_out={result.timed_out}"
    )
    return 0 if result.packets > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
