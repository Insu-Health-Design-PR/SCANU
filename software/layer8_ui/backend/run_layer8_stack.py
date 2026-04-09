"""Run integrated Layer 6 -> Layer 7 -> Layer 8 stack for demo/testing."""

from __future__ import annotations

import argparse
import json
import threading
import time
from dataclasses import asdict
from pathlib import Path

import uvicorn

from software.layer1_sensor_hub import MultiSensorHub
from software.layer1_sensor_hub.infeneon import IfxLtr11PresenceProvider, MockPresenceProvider, PresenceSource
from software.layer1_sensor_hub.mmwave import RadarConfigurator, SerialManager, TLVParser, UARTSource
from software.layer6_state_machine import Layer6Orchestrator, SystemHealth
from software.layer7_alerts import L6ToL7Bridge

from .app import create_app
from .integration import L6L7ToL8Bridge


def _simulate_raw(frame: int, radar_id: str) -> dict:
    return {
        "frame_number": frame,
        "timestamp_ms": time.time() * 1000.0,
        "radar_id": radar_id,
        "thermal_presence": 0.2 if frame % 7 < 4 else 0.7,
        "presence_frame": {
            "presence_raw": 0.6 if frame % 5 else 0.2,
            "motion_raw": 0.55 if frame % 3 else 0.1,
        },
        "mmwave_frame": {
            "points": [1] * (frame % 10),
        },
    }


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


def _producer_loop(
    *,
    stop_event: threading.Event,
    l8_bridge: L6L7ToL8Bridge,
    args: argparse.Namespace,
    orchestrator: Layer6Orchestrator,
) -> None:
    l7_bridge = L6ToL7Bridge()

    hub = None
    serial_mgr = None

    try:
        if args.mode == "live":
            hub, serial_mgr = _build_live_hub(args)

        frame = 0
        while not stop_event.is_set():
            frame += 1
            if args.max_frames > 0 and frame > args.max_frames:
                break

            if args.mode == "live":
                raw = hub.read_frame(mmwave_timeout_ms=args.mmwave_timeout_ms)
                health = SystemHealth(has_fault=False, sensor_online_count=1)
            else:
                raw = _simulate_raw(frame=frame, radar_id=args.radar_id)
                health = SystemHealth(has_fault=False, sensor_online_count=1)

            state_event, snapshot, action_request = orchestrator.tick(raw, health=health, radar_id=args.radar_id)
            alert = l7_bridge.ingest(state_event, snapshot=snapshot, action_request=action_request)
            l8_bridge.ingest(snapshot=snapshot, alert=alert, action_request=action_request)

            if args.print_events:
                payload = {
                    "event": asdict(state_event),
                    "snapshot": asdict(snapshot),
                    "action_request": asdict(action_request) if action_request else None,
                    "alert": asdict(alert),
                }
                print(json.dumps(payload, indent=2, default=str))

            if args.interval_s > 0:
                time.sleep(args.interval_s)
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
    parser = argparse.ArgumentParser(description="Run integrated L6 -> L7 -> L8 stack")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)

    parser.add_argument("--mode", choices=("simulate", "live"), default="simulate")
    parser.add_argument("--radar-id", default="radar_main")
    parser.add_argument("--max-frames", type=int, default=0, help="0 = run producer forever")
    parser.add_argument("--interval-s", type=float, default=0.2)
    parser.add_argument("--print-events", action="store_true")
    parser.add_argument("--mmwave-timeout-ms", type=int, default=200)

    parser.add_argument("--cli-port", default=None)
    parser.add_argument("--data-port", default=None)
    parser.add_argument("--config", default=None)
    parser.add_argument("--skip-mmwave-config", action="store_true")
    parser.add_argument("--mmwave", choices=("on", "off"), default="off")

    parser.add_argument("--presence", choices=("mock", "ifx", "off"), default="mock")
    parser.add_argument("--ifx-uuid", default=None)

    parser.add_argument("--thermal", choices=("on", "off"), default="off")
    parser.add_argument("--thermal-device", type=int, default=0)
    parser.add_argument("--thermal-width", type=int, default=640)
    parser.add_argument("--thermal-height", type=int, default=480)
    parser.add_argument("--thermal-fps", type=int, default=30)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    orchestrator = Layer6Orchestrator(primary_radar_id=args.radar_id)
    l8_bridge = L6L7ToL8Bridge()
    app = create_app(store=l8_bridge.store, publisher=l8_bridge.publisher, orchestrator=orchestrator)

    stop_event = threading.Event()
    producer = threading.Thread(
        target=_producer_loop,
        kwargs={
            "stop_event": stop_event,
            "l8_bridge": l8_bridge,
            "args": args,
            "orchestrator": orchestrator,
        },
        daemon=True,
    )
    producer.start()

    try:
        uvicorn.run(app, host=args.host, port=args.port)
    finally:
        stop_event.set()
        producer.join(timeout=2.0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
