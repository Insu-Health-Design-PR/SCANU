"""Run mmWave + Infeneon + Thermal live from one terminal command."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
import numpy as np

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
from software.layer1_sensor_hub.mmwave import (
    RadarConfigurator,
    RadarPointFilterConfig,
    SerialManager,
    TLVParser,
    UARTSource,
    filter_detected_points,
)


@dataclass
class RuntimeHandles:
    """Resources that require explicit cleanup."""

    serial_manager: Optional[SerialManager] = None
    hub: Optional[MultiSensorHub] = None


@dataclass(frozen=True)
class MMWaveSummary:
    raw_points: int
    filtered_points: int
    moving_points: int
    person_score: float
    compact_object_score: float


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
        default="software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg",
        help="Path to mmWave .cfg file used for configuration",
    )
    parser.add_argument("--skip-mmwave-config", action="store_true")
    parser.add_argument("--mmw-min-range-m", type=float, default=0.35)
    parser.add_argument("--mmw-max-range-m", type=float, default=6.0)
    parser.add_argument("--mmw-max-azimuth-deg", type=float, default=65.0)
    parser.add_argument("--mmw-min-z-m", type=float, default=-1.0)
    parser.add_argument("--mmw-max-z-m", type=float, default=2.5)
    parser.add_argument("--mmw-min-snr-db", type=float, default=6.0)
    parser.add_argument("--mmw-max-abs-doppler-mps", type=float, default=6.0)

    parser.add_argument("--presence", choices=("mock", "ifx", "off"), default="mock")
    parser.add_argument("--ifx-uuid", type=str, default=None)

    parser.add_argument("--thermal", choices=("on", "off"), default="on")
    parser.add_argument("--thermal-device", type=int, default=0)
    parser.add_argument("--thermal-width", type=int, default=640)
    parser.add_argument("--thermal-height", type=int, default=480)
    parser.add_argument("--thermal-fps", type=int, default=30)
    return parser


def _point_array(points: list[object]) -> np.ndarray:
    if not points:
        return np.zeros((0, 4), dtype=np.float32)
    rows = []
    for p in points:
        rows.append(
            [
                float(getattr(p, "x", 0.0)),
                float(getattr(p, "y", 0.0)),
                float(getattr(p, "z", 0.0)),
                float(getattr(p, "doppler", 0.0)),
            ]
        )
    return np.asarray(rows, dtype=np.float32)


def summarize_mmwave(parsed: object, cfg: RadarPointFilterConfig) -> MMWaveSummary:
    raw_points = list(getattr(parsed, "points", []) or [])
    filtered = filter_detected_points(raw_points, cfg)
    arr = _point_array(filtered)

    raw_count = len(raw_points)
    filt_count = len(filtered)
    if filt_count == 0:
        return MMWaveSummary(
            raw_points=raw_count,
            filtered_points=0,
            moving_points=0,
            person_score=0.0,
            compact_object_score=0.0,
        )

    speed = np.abs(arr[:, 3])
    moving_points = int(np.sum(speed >= 0.12))

    x_span = float(np.max(arr[:, 0]) - np.min(arr[:, 0]))
    y_span = float(np.max(arr[:, 1]) - np.min(arr[:, 1]))
    z_span = float(np.max(arr[:, 2]) - np.min(arr[:, 2]))
    moving_ratio = float(moving_points / max(1, filt_count))

    person_score = 0.0
    if filt_count >= 8:
        person_score += 0.35
    elif filt_count >= 4:
        person_score += 0.20
    if 0.2 <= x_span <= 1.2:
        person_score += 0.20
    if 0.4 <= y_span <= 2.8:
        person_score += 0.25
    if 0.4 <= z_span <= 2.2:
        person_score += 0.10
    if moving_ratio >= 0.2:
        person_score += 0.10
    person_score = max(0.0, min(1.0, person_score))

    # This is only a coarse candidate score, not classification.
    compact_object_score = 0.0
    if filt_count >= 1 and filt_count <= 10:
        compact_object_score += 0.30
    if x_span <= 0.45 and y_span <= 0.55 and z_span <= 0.55:
        compact_object_score += 0.35
    if float(np.percentile(speed, 90)) >= 0.25:
        compact_object_score += 0.20
    if person_score >= 0.45:
        compact_object_score += 0.15
    compact_object_score = max(0.0, min(1.0, compact_object_score))

    return MMWaveSummary(
        raw_points=raw_count,
        filtered_points=filt_count,
        moving_points=moving_points,
        person_score=person_score,
        compact_object_score=compact_object_score,
    )


def summarize_frame(frame: object, mmw_filter_cfg: RadarPointFilterConfig) -> str:
    mmw = getattr(frame, "mmwave_frame", None)
    prs = getattr(frame, "presence_frame", None)
    thm = getattr(frame, "thermal_frame_bgr", None)

    mmw_summary = "mmw=off"
    if mmw is not None:
        mmw_stats = summarize_mmwave(mmw, mmw_filter_cfg)
        mmw_summary = (
            "mmw=on "
            f"pts(raw/f)={mmw_stats.raw_points}/{mmw_stats.filtered_points} "
            f"moving={mmw_stats.moving_points} "
            f"person={mmw_stats.person_score:.2f} "
            f"compact_obj={mmw_stats.compact_object_score:.2f}"
        )

    prs_summary = "ifx=off"
    if prs is not None:
        prs_summary = f"ifx=on presence={prs.presence_raw:.3f} motion={prs.motion_raw:.3f} dist={prs.distance_m:.2f}m"

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
    mmw_filter_cfg: RadarPointFilterConfig,
    printer: Callable[[str], None] = print,
    sleeper: Callable[[float], None] = time.sleep,
) -> int:
    count = 0
    while max_frames == 0 or count < max_frames:
        frame = hub.read_frame(mmwave_timeout_ms=mmwave_timeout_ms)
        printer(summarize_frame(frame, mmw_filter_cfg))
        count += 1
        if interval_s > 0:
            sleeper(interval_s)
    return count


def main() -> int:
    args = build_parser().parse_args()
    mmw_filter_cfg = RadarPointFilterConfig(
        min_range_m=args.mmw_min_range_m,
        max_range_m=args.mmw_max_range_m,
        max_abs_azimuth_deg=args.mmw_max_azimuth_deg,
        min_z_m=args.mmw_min_z_m,
        max_z_m=args.mmw_max_z_m,
        min_snr_db=args.mmw_min_snr_db,
        max_abs_doppler_mps=args.mmw_max_abs_doppler_mps,
    )
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
            mmw_filter_cfg=mmw_filter_cfg,
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
