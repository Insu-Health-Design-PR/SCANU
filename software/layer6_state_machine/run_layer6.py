#!/usr/bin/env python3
"""Operational CLI for Layer 6 state + control plane."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from software.layer1_sensor_hub import MultiSensorHub
from software.layer1_sensor_hub.infeneon import IfxLtr11PresenceProvider, MockPresenceProvider, PresenceSource
from software.layer1_sensor_hub.mmwave import RadarConfigurator, SerialManager, TLVParser, UARTSource

from .models import RadarRuntimeSpec, SystemHealth
from .orchestrator import Layer6Orchestrator
from .sensor_control import SensorControlManager


def _parse_aux_specs(values: Iterable[str]) -> list[RadarRuntimeSpec]:
    specs: list[RadarRuntimeSpec] = []
    for raw in values:
        # Expected: radar_aux_1:/dev/ttyUSB2:/dev/ttyUSB3:/path/to/cfg(optional)
        parts = raw.split(":")
        if len(parts) < 3:
            raise ValueError(f"Invalid --aux-radar format: {raw}")
        specs.append(
            RadarRuntimeSpec(
                radar_id=parts[0],
                config_port=parts[1] or None,
                data_port=parts[2] or None,
                default_config_path=parts[3] if len(parts) > 3 and parts[3] else None,
            )
        )
    return specs


def _build_control_manager(args: argparse.Namespace) -> SensorControlManager:
    specs = [
        RadarRuntimeSpec(
            radar_id=args.radar_id,
            config_port=args.cli_port,
            data_port=args.data_port,
            default_config_path=args.config,
        )
    ]
    specs.extend(_parse_aux_specs(args.aux_radar))
    return SensorControlManager(radars=specs)


def _build_live_hub(args: argparse.Namespace) -> tuple[MultiSensorHub, SerialManager | None]:
    serial_mgr = None
    mmwave_source = None
    mmwave_parser = None

    if args.mmwave == "on":
        serial_mgr = SerialManager()
        ports = serial_mgr.find_radar_ports(
            verbose=False,
            config_port=args.cli_port,
            data_port=args.data_port,
        )
        serial_mgr.connect(ports.config_port, ports.data_port)

        if not args.skip_mmwave_config:
            configurator = RadarConfigurator(serial_mgr)
            if args.config:
                result = configurator.configure_from_file(Path(args.config))
            else:
                result = configurator.configure(None)
            if not result.success:
                raise RuntimeError(f"mmWave configure failed: {result.errors[:3]}")

        mmwave_source = UARTSource(serial_mgr)
        mmwave_parser = TLVParser()

    presence_source = None
    if args.presence == "mock":
        presence_source = PresenceSource(MockPresenceProvider())
    elif args.presence == "ifx":
        presence_source = PresenceSource(IfxLtr11PresenceProvider(uuid=args.ifx_uuid))

    thermal_source = None
    if args.thermal == "on":
        from software.layer1_sensor_hub.thermal import ThermalCameraSource

        thermal_source = ThermalCameraSource(
            device=args.thermal_device,
            width=args.thermal_width,
            height=args.thermal_height,
            fps=args.thermal_fps,
        )

    hub = MultiSensorHub(
        mmwave_source=mmwave_source,
        mmwave_parser=mmwave_parser,
        presence_source=presence_source,
        thermal_source=thermal_source,
    )
    return hub, serial_mgr


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


def _run_command(orchestrator: Layer6Orchestrator, args: argparse.Namespace) -> int:
    mode = args.mode
    frame_count = 0

    hub = None
    serial_mgr = None

    try:
        if mode == "live":
            hub, serial_mgr = _build_live_hub(args)

        while args.max_frames == 0 or frame_count < args.max_frames:
            if mode == "simulate":
                raw = {
                    "frame_number": frame_count + 1,
                    "timestamp_ms": time.time() * 1000.0,
                    "radar_id": args.radar_id,
                    "thermal_presence": 0.2 if frame_count % 7 < 4 else 0.7,
                    "presence_frame": {
                        "presence_raw": 0.6 if frame_count % 5 else 0.2,
                        "motion_raw": 0.55 if frame_count % 3 else 0.1,
                    },
                    "mmwave_frame": {
                        "points": [1] * (frame_count % 10),
                    },
                }
                health = SystemHealth(has_fault=False, sensor_online_count=1)
            else:
                raw = hub.read_frame(mmwave_timeout_ms=args.mmwave_timeout_ms)
                health = SystemHealth(has_fault=False, sensor_online_count=1)

            event, snapshot, action = orchestrator.tick(raw, health=health, radar_id=args.radar_id)
            payload = {
                "event": asdict(event),
                "snapshot": asdict(snapshot),
                "action_request": asdict(action) if action is not None else None,
            }
            _print_json(payload)
            frame_count += 1

            if args.interval_s > 0:
                time.sleep(args.interval_s)

        return 0
    finally:
        if hub is not None:
            try:
                hub.close()
            except Exception:
                pass
        if serial_mgr is not None:
            try:
                serial_mgr.disconnect()
            except Exception:
                pass


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Layer 6 runner (state + control plane)")

    p.add_argument("--radar-id", default="radar_main")
    p.add_argument("--cli-port", default=None)
    p.add_argument("--data-port", default=None)
    p.add_argument("--config", default=None)
    p.add_argument(
        "--aux-radar",
        action="append",
        default=[],
        help="format: radar_aux_1:/dev/ttyUSB2:/dev/ttyUSB3:/path/to/cfg(optional)",
    )

    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run Layer 6 loop")
    run.add_argument("--mode", choices=("simulate", "live"), default="simulate")
    run.add_argument("--max-frames", type=int, default=30, help="0 = run forever")
    run.add_argument("--interval-s", type=float, default=0.2)
    run.add_argument("--mmwave-timeout-ms", type=int, default=200)

    run.add_argument("--mmwave", choices=("on", "off"), default="off")
    run.add_argument("--skip-mmwave-config", action="store_true")

    run.add_argument("--presence", choices=("mock", "ifx", "off"), default="mock")
    run.add_argument("--ifx-uuid", default=None)

    run.add_argument("--thermal", choices=("on", "off"), default="off")
    run.add_argument("--thermal-device", type=int, default=0)
    run.add_argument("--thermal-width", type=int, default=640)
    run.add_argument("--thermal-height", type=int, default=480)
    run.add_argument("--thermal-fps", type=int, default=30)

    sub.add_parser("status", help="Get radar status")

    reconfig = sub.add_parser("reconfig", help="Apply radar configuration")
    reconfig.add_argument("--config-text", default=None)

    sub.add_parser("reset", help="Soft reset radar")

    kill = sub.add_parser("kill", help="Kill holder processes (manual-only)")
    kill.add_argument("--force", action="store_true")
    kill.add_argument("--confirm-manual", action="store_true")

    usb = sub.add_parser("usb-reset", help="USB reset (manual-only)")
    usb.add_argument("--confirm-manual", action="store_true")

    return p


def main() -> int:
    args = build_parser().parse_args()
    control = _build_control_manager(args)
    orchestrator = Layer6Orchestrator(sensor_control=control, primary_radar_id=args.radar_id)

    if args.command == "run":
        return _run_command(orchestrator, args)

    if args.command == "status":
        _print_json(asdict(orchestrator.get_status(args.radar_id)))
        return 0

    if args.command == "reconfig":
        result = orchestrator.apply_config(args.radar_id, config_path=args.config, config_text=args.config_text)
        _print_json(asdict(result))
        return 0 if result.success else 1

    if args.command == "reset":
        result = orchestrator.reset_soft(args.radar_id)
        _print_json(asdict(result))
        return 0 if result.success else 1

    if args.command == "kill":
        result = orchestrator.kill_holders(
            args.radar_id,
            force=bool(args.force),
            manual_confirm=bool(args.confirm_manual),
        )
        _print_json(asdict(result))
        return 0 if result.success else 1

    if args.command == "usb-reset":
        result = orchestrator.usb_reset(args.radar_id, manual_confirm=bool(args.confirm_manual))
        _print_json(asdict(result))
        return 0 if result.success else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
