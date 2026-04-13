"""Run integrated Layer 6 -> Layer 7 -> Layer 8 stack for demo/testing."""

from __future__ import annotations

import argparse
import base64
import json
import threading
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import uvicorn
try:
    import cv2
except Exception:  # pragma: no cover - optional dependency in some environments
    cv2 = None

from software.layer1_sensor_hub import MultiSensorHub
from software.layer1_sensor_hub.infeneon import IfxLtr11PresenceProvider, MockPresenceProvider, PresenceSource
from software.layer1_sensor_hub.mmwave import RadarConfigurator, SerialManager, TLVParser, UARTSource
from software.layer6_state_machine import Layer6Orchestrator, SystemHealth
from software.layer7_alerts import L6ToL7Bridge

from .app import create_app
from .integration import L6L7ToL8Bridge
from .visual_state_store import VisualStateStore
from .websocket_stream import WebSocketStream


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


def _encode_jpeg_b64(frame_bgr: np.ndarray | None) -> str | None:
    if cv2 is None:
        return None
    if frame_bgr is None:
        return None
    ok, encoded = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
    if not ok:
        return None
    return base64.b64encode(encoded.tobytes()).decode("ascii")


def _extract_point_cloud(parsed_frame: object | None, *, limit: int = 256) -> list[dict[str, float]]:
    points = getattr(parsed_frame, "points", []) if parsed_frame is not None else []
    payload: list[dict[str, float]] = []
    for p in points or []:
        payload.append(
            {
                "x": float(getattr(p, "x", 0.0)),
                "y": float(getattr(p, "y", 0.0)),
                "z": float(getattr(p, "z", 0.0)),
                "doppler": float(getattr(p, "doppler", 0.0)),
                "snr": float(getattr(p, "snr", 0.0)),
            }
        )
        if len(payload) >= limit:
            break
    return payload


def _simulate_visual(frame: int, *, width: int, height: int) -> dict:
    ts_ms = time.time() * 1000.0

    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    thermal = np.zeros((height, width, 3), dtype=np.uint8)
    if cv2 is not None:
        cv2.putText(rgb, "RGB (simulate)", (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 240, 240), 2)
        cv2.putText(thermal, "Thermal (simulate)", (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 240, 240), 2)
        cv2.circle(rgb, (80 + (frame * 9) % max(120, width - 40), height // 2), 28, (0, 190, 255), -1)
        cv2.rectangle(thermal, (20, 50), (min(width - 20, 20 + (frame * 7) % max(120, width - 40)), height - 50), (0, 0, 255), -1)

    cloud: list[dict[str, float]] = []
    for idx in range(36):
        x = -0.8 + (idx % 9) * 0.2
        y = 0.5 + ((frame + idx) % 12) * 0.18
        z = -0.4 + (idx % 5) * 0.2
        cloud.append({"x": x, "y": y, "z": z, "doppler": 0.1 * ((idx % 3) - 1), "snr": 7.0 + (idx % 6)})

    presence = {
        "presence_raw": 0.35 + (0.45 if frame % 10 > 5 else 0.0),
        "motion_raw": 0.4 + (0.4 if frame % 6 > 2 else 0.0),
        "distance_m": 1.8 + 0.2 * np.sin(frame / 8.0),
    }

    return {
        "timestamp_ms": ts_ms,
        "source_mode": "simulate_l1_bridge",
        "rgb_jpeg_b64": _encode_jpeg_b64(rgb),
        "thermal_jpeg_b64": _encode_jpeg_b64(thermal),
        "point_cloud": cloud,
        "presence": presence,
        "meta": {
            "ready": True,
            "rgb_enabled": True,
            "thermal_enabled": True,
            "point_cloud_enabled": True,
            "presence_enabled": True,
        },
    }


def _build_visual_from_live(raw: object, *, rgb_frame: np.ndarray | None, mode: str) -> dict:
    ts_ms = float(getattr(raw, "timestamp_ms", time.time() * 1000.0))
    mmwave = getattr(raw, "mmwave_frame", None)
    presence_frame = getattr(raw, "presence_frame", None)
    thermal_frame = getattr(raw, "thermal_frame_bgr", None)

    presence = None
    if presence_frame is not None:
        distance = float(getattr(presence_frame, "distance_m", -1.0))
        presence = {
            "presence_raw": float(getattr(presence_frame, "presence_raw", 0.0)),
            "motion_raw": float(getattr(presence_frame, "motion_raw", 0.0)),
            "distance_m": None if distance < 0 else distance,
        }

    return {
        "timestamp_ms": ts_ms,
        "source_mode": mode,
        "rgb_jpeg_b64": _encode_jpeg_b64(rgb_frame),
        "thermal_jpeg_b64": _encode_jpeg_b64(thermal_frame),
        "point_cloud": _extract_point_cloud(mmwave),
        "presence": presence,
        "meta": {
            "ready": True,
            "rgb_enabled": rgb_frame is not None,
            "thermal_enabled": thermal_frame is not None,
            "point_cloud_enabled": mmwave is not None,
            "presence_enabled": presence is not None,
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
    visual_store: VisualStateStore,
    args: argparse.Namespace,
    orchestrator: Layer6Orchestrator,
) -> None:
    l7_bridge = L6ToL7Bridge()

    hub = None
    serial_mgr = None
    rgb_cap = None

    try:
        if args.mode == "live":
            hub, serial_mgr = _build_live_hub(args)
            if args.rgb == "on" and cv2 is not None:
                rgb_cap = cv2.VideoCapture(int(args.rgb_device))
                if rgb_cap.isOpened():
                    rgb_cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(args.rgb_width))
                    rgb_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(args.rgb_height))
                    rgb_cap.set(cv2.CAP_PROP_FPS, int(args.rgb_fps))

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

            if args.visual == "on":
                if args.mode == "simulate":
                    visual_payload = _simulate_visual(
                        frame=frame,
                        width=int(args.visual_width),
                        height=int(args.visual_height),
                    )
                else:
                    rgb_frame = None
                    if rgb_cap is not None and rgb_cap.isOpened():
                        ok, frame_bgr = rgb_cap.read()
                        if ok and frame_bgr is not None:
                            if cv2 is not None:
                                rgb_frame = cv2.resize(
                                    frame_bgr,
                                    (int(args.visual_width), int(args.visual_height)),
                                    interpolation=cv2.INTER_LINEAR,
                                )
                            else:
                                rgb_frame = frame_bgr
                    visual_payload = _build_visual_from_live(raw, rgb_frame=rgb_frame, mode="live_l1_bridge")

                visual_store.update(visual_payload)
                l8_bridge.publisher.publish(WebSocketStream.encode_visual_update(visual_payload))

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
        if rgb_cap is not None:
            try:
                rgb_cap.release()
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

    parser.add_argument("--visual", choices=("on", "off"), default="on")
    parser.add_argument("--visual-width", type=int, default=640)
    parser.add_argument("--visual-height", type=int, default=480)

    parser.add_argument("--rgb", choices=("on", "off"), default="off")
    parser.add_argument("--rgb-device", type=int, default=0)
    parser.add_argument("--rgb-width", type=int, default=640)
    parser.add_argument("--rgb-height", type=int, default=480)
    parser.add_argument("--rgb-fps", type=int, default=30)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    orchestrator = Layer6Orchestrator(primary_radar_id=args.radar_id)
    l8_bridge = L6L7ToL8Bridge()
    visual_store = VisualStateStore()
    app = create_app(
        store=l8_bridge.store,
        publisher=l8_bridge.publisher,
        orchestrator=orchestrator,
        visual_store=visual_store,
    )

    stop_event = threading.Event()
    producer = threading.Thread(
        target=_producer_loop,
        kwargs={
            "stop_event": stop_event,
            "l8_bridge": l8_bridge,
            "visual_store": visual_store,
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
