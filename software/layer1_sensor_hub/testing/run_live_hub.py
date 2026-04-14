"""Run mmWave + Infeneon + Thermal live from one terminal command."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

# Support direct script execution on Jetson from repository root.
import sys

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from software.layer1_sensor_hub import MultiSensorHub
from software.layer1_sensor_hub.infeneon import (  # type: ignore
    IfxLtr11PresenceProvider,
    MockPresenceProvider,
    PresenceSource,
)
from software.layer1_sensor_hub.mmwave import RadarConfigurator, SerialManager, TLVParser, UARTSource


@dataclass
class RuntimeHandles:
    """Resources that require explicit cleanup."""

    serial_manager: Optional[SerialManager] = None
    hub: Optional[MultiSensorHub] = None


def resolve_config_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate

    cwd_candidate = (Path.cwd() / candidate).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    repo_candidate = (REPO_ROOT / candidate).resolve()
    return repo_candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Live runner for layer1_sensor_hub (3 sensors)")
    parser.add_argument("--max-frames", type=int, default=0, help="0 = run forever")
    parser.add_argument("--interval-s", type=float, default=0.1, help="Loop interval in seconds")
    parser.add_argument("--mmwave-timeout-ms", type=int, default=200)

    parser.add_argument("--mmwave", choices=("on", "off"), default="on")
    parser.add_argument("--cli-port", type=str, default=None)
    parser.add_argument("--data-port", type=str, default=None)
    parser.add_argument(
        "--config",
        type=str,
        default="software/layer1_sensor_hub/testing/configs/mmwave_main.cfg",
        help="Path to mmWave .cfg file used for configuration",
    )
    parser.add_argument("--skip-mmwave-config", action="store_true")

    parser.add_argument("--presence", choices=("mock", "ifx", "off"), default="mock")
    parser.add_argument("--ifx-uuid", type=str, default=None)

    parser.add_argument("--thermal", choices=("on", "off"), default="on")
    parser.add_argument("--thermal-device", type=int, default=0)
    parser.add_argument("--thermal-width", type=int, default=640)
    parser.add_argument("--thermal-height", type=int, default=480)
    parser.add_argument("--thermal-fps", type=int, default=30)
    return parser


def summarize_frame(frame: object) -> str:
    mmw = getattr(frame, "mmwave_frame", None)
    prs = getattr(frame, "presence_frame", None)
    thm = getattr(frame, "thermal_frame_bgr", None)

    mmw_summary = "mmw=off"
    if mmw is not None:
        points = len(getattr(mmw, "points", []))
        mmw_summary = f"mmw=on points={points}"

    prs_summary = "ifx=off"
    if prs is not None:
        dist = getattr(prs, "distance_m", -1.0)
        dist_text = f"{dist:.2f}m" if isinstance(dist, (int, float)) and dist >= 0 else "N/A"
        prs_summary = f"ifx=on presence={prs.presence_raw:.3f} motion={prs.motion_raw:.3f} dist={dist_text}"

    thm_summary = "thermal=off"
    if thm is not None:
        shape = getattr(thm, "shape", None)
        if shape is not None and len(shape) >= 2:
            thm_summary = f"thermal=on {shape[1]}x{shape[0]}"
        else:
            thm_summary = "thermal=on"

    frame_no = getattr(frame, "frame_number", -1)
    return f"frame={frame_no} | {mmw_summary} | {prs_summary} | {thm_summary}"


def _build_mmwave(args: argparse.Namespace) -> tuple[Optional[SerialManager], Optional[UARTSource], Optional[TLVParser]]:
    if args.mmwave == "off":
        return None, None, None

    serial_mgr = SerialManager()
    if args.cli_port and args.data_port:
        ports = serial_mgr.find_radar_ports(verbose=False, config_port=args.cli_port, data_port=args.data_port)
    else:
        ports = serial_mgr.find_radar_ports(verbose=False)
    serial_mgr.connect(ports.config_port, ports.data_port)

    if not args.skip_mmwave_config:
        cfg_path = resolve_config_path(args.config)
        if not cfg_path.exists():
            raise RuntimeError(
                f"mmWave config file not found: {cfg_path}. "
                "Add a .cfg under testing/configs or pass --config explicitly."
            )
        config_result = RadarConfigurator(serial_mgr).configure_from_file(cfg_path)
        if not config_result.success:
            raise RuntimeError(f"mmWave configure failed: {config_result.errors[:3]}")

    return serial_mgr, UARTSource(serial_mgr), TLVParser()


def _build_presence(args: argparse.Namespace) -> Optional[PresenceSource]:
    if args.presence == "off":
        return None
    if args.presence == "mock":
        return PresenceSource(MockPresenceProvider())
    return PresenceSource(IfxLtr11PresenceProvider(uuid=args.ifx_uuid))


def _build_thermal(args: argparse.Namespace) -> Optional[object]:
    if args.thermal == "off":
        return None
    from software.layer1_sensor_hub.thermal import ThermalCameraSource

    return ThermalCameraSource(
        device=args.thermal_device,
        width=args.thermal_width,
        height=args.thermal_height,
        fps=args.thermal_fps,
    )


def run_loop(
    hub: MultiSensorHub,
    *,
    max_frames: int,
    interval_s: float,
    mmwave_timeout_ms: int,
    printer: Callable[[str], None] = print,
    sleeper: Callable[[float], None] = time.sleep,
) -> int:
    count = 0
    while max_frames == 0 or count < max_frames:
        frame = hub.read_frame(mmwave_timeout_ms=mmwave_timeout_ms)
        printer(summarize_frame(frame))
        count += 1
        if interval_s > 0:
            sleeper(interval_s)
    return count


def main() -> int:
    args = build_parser().parse_args()
    handles = RuntimeHandles()
    try:
        mmw_mgr, mmw_source, mmw_parser = _build_mmwave(args)
        handles.serial_manager = mmw_mgr

        presence_source = _build_presence(args)
        thermal_source = _build_thermal(args)

        hub = MultiSensorHub(
            mmwave_source=mmw_source,
            mmwave_parser=mmw_parser,
            presence_source=presence_source,
            thermal_source=thermal_source,
        )
        handles.hub = hub

        print("Starting live sensor loop. Press Ctrl+C to stop.")
        run_loop(
            hub,
            max_frames=args.max_frames,
            interval_s=args.interval_s,
            mmwave_timeout_ms=args.mmwave_timeout_ms,
        )
        return 0
    except KeyboardInterrupt:
        print("\nStopped by user.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        if handles.hub is not None:
            try:
                handles.hub.close()
            except Exception:
                pass
        if handles.serial_manager is not None:
            try:
                handles.serial_manager.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
