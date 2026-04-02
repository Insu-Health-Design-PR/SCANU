#!/usr/bin/env python3
"""Capture mmWave + thermal + Infineon with rich mmWave JSON and risk features."""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from collections import deque
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from software.layer1_sensor_hub.infeneon import IfxLtr11PresenceProvider, MockPresenceProvider, PresenceSource
from software.layer1_sensor_hub.mmwave import RadarConfigurator, SerialManager, TLVParser, UARTSource
from software.layer1_sensor_hub.thermal import ThermalCameraSource


def resolve_config_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate
    cwd_candidate = (Path.cwd() / candidate).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (REPO_ROOT / candidate).resolve()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def render_radar_panel(width: int, height: int, parsed_frame: Optional[object]) -> np.ndarray:
    panel = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.putText(panel, "mmWave Radar", (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

    center_x = width // 2
    bottom_y = height - 30
    meters_to_px = max(40, min(width, height) // 6)

    cv2.line(panel, (center_x, bottom_y), (center_x, 45), (70, 70, 70), 1)
    cv2.line(panel, (40, bottom_y), (width - 40, bottom_y), (70, 70, 70), 1)
    cv2.putText(panel, "X", (width - 24, bottom_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (130, 130, 130), 1)
    cv2.putText(panel, "Y", (center_x + 6, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (130, 130, 130), 1)

    points = getattr(parsed_frame, "points", []) if parsed_frame is not None else []
    points = points or []
    for p in points:
        x_m = float(getattr(p, "x", 0.0))
        y_m = float(getattr(p, "y", 0.0))
        px = int(center_x + x_m * meters_to_px)
        py = int(bottom_y - y_m * meters_to_px)
        if 0 <= px < width and 0 <= py < height:
            cv2.circle(panel, (px, py), 4, (0, 220, 255), -1)

    cv2.putText(panel, f"points: {len(points)}", (10, height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 2)
    return panel


def render_infineon_panel(width: int, height: int, presence_hist: deque[float], motion_hist: deque[float]) -> np.ndarray:
    panel = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.putText(panel, "Infineon Presence", (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
    if not presence_hist:
        cv2.putText(panel, "no data", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (180, 180, 180), 2)
        return panel

    p = np.asarray(presence_hist, dtype=np.float32)
    m = np.asarray(motion_hist, dtype=np.float32) if len(motion_hist) == len(presence_hist) else np.zeros_like(p)
    max_v = float(np.percentile(p, 98)) if p.size >= 5 else float(np.max(p))
    max_v = max(max_v, 1e-6)
    norm = np.clip(p / max_v, 0.0, 1.0)

    left, right = 10, width - 10
    top, bottom = 80, height - 20
    cv2.rectangle(panel, (left, top), (right, bottom), (70, 70, 70), 1)
    xs = np.linspace(left, right, norm.size, dtype=np.int32)
    ys = (bottom - norm * (bottom - top)).astype(np.int32)
    pts = np.column_stack([xs, ys]).reshape((-1, 1, 2))
    cv2.polylines(panel, [pts], isClosed=False, color=(0, 200, 255), thickness=2)

    cur_p = float(p[-1])
    cur_m = float(m[-1])
    cv2.putText(panel, f"presence_raw: {cur_p:.5f}", (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 2)
    motion_color = (0, 255, 0) if cur_m >= 0.5 else (90, 90, 90)
    cv2.circle(panel, (right - 15, 52), 10, motion_color, -1)
    cv2.putText(panel, "motion", (right - 95, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (210, 210, 210), 2)
    return panel


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Capture all sensors with rich mmWave point JSON and risk features")
    p.add_argument("--frames", "-n", type=int, default=300, help="Frame count")
    p.add_argument("--interval-s", type=float, default=0.1, help="Loop delay between frames")
    p.add_argument("--mmwave-timeout-ms", type=int, default=200, help="mmWave frame read timeout")

    p.add_argument("--cli-port", default=None, help="mmWave CLI port (optional; auto-detect when omitted)")
    p.add_argument("--data-port", default=None, help="mmWave DATA port (optional; auto-detect when omitted)")
    p.add_argument("--config", "-c", required=True, help="Path to mmWave .cfg file")
    p.add_argument("--skip-mmwave-config", action="store_true", help="Skip sending .cfg")

    p.add_argument("--presence", choices=("mock", "ifx", "off"), default="ifx", help="Infineon provider mode")
    p.add_argument("--ifx-uuid", default=None, help="Optional Infineon UUID")

    p.add_argument("--thermal-device", type=int, default=0)
    p.add_argument("--thermal-width", type=int, default=640)
    p.add_argument("--thermal-height", type=int, default=480)
    p.add_argument("--thermal-fps", type=int, default=30)

    p.add_argument("--video", "-vout", default="all_sensors_rich.mp4", help="Output MP4 path")
    p.add_argument("--output", "-o", default="all_sensors_rich.json", help="Output JSON path")
    p.add_argument("--panel-width", type=int, default=640, help="Per-sensor panel width")
    p.add_argument("--panel-height", type=int, default=480, help="Per-sensor panel height")
    p.add_argument("--verbose", "-v", action="store_true")

    # Risk-feature parameters (simple baseline heuristic, tune with data).
    p.add_argument("--roi-half-width-m", type=float, default=0.25, help="Torso ROI half-width in X around centroid")
    p.add_argument("--roi-y-back-m", type=float, default=0.15, help="Torso ROI back extent in Y from centroid")
    p.add_argument("--roi-y-front-m", type=float, default=0.20, help="Torso ROI front extent in Y from centroid")
    p.add_argument("--snr-iqr-k", type=float, default=1.5, help="Reflective threshold factor: median + k*IQR")
    p.add_argument("--min-roi-points", type=int, default=3, help="Minimum points in ROI to score reflection")
    p.add_argument("--persistent-threshold", type=float, default=0.35, help="Reflective fraction threshold for persistence")
    p.add_argument("--persist-window", type=int, default=20, help="Persistence window size (M)")
    p.add_argument("--persist-required", type=int, default=12, help="Required active frames in window (N)")
    p.add_argument("--ema-alpha", type=float, default=0.2, help="EMA alpha for reflective fraction")
    return p


def build_presence_source(mode: str, ifx_uuid: Optional[str]) -> Optional[PresenceSource]:
    if mode == "off":
        return None
    if mode == "mock":
        return PresenceSource(MockPresenceProvider())
    return PresenceSource(IfxLtr11PresenceProvider(uuid=ifx_uuid))


def connect_mmwave_with_recovery(serial_mgr: SerialManager, cli_port: Optional[str], data_port: Optional[str]) -> tuple[str, str]:
    candidates: list[tuple[str, str]] = []
    if cli_port and data_port:
        candidates.append((str(cli_port), str(data_port)))
        if str(cli_port) != str(data_port):
            candidates.append((str(data_port), str(cli_port)))
    else:
        ports = serial_mgr.find_radar_ports(verbose=False, config_port=cli_port, data_port=data_port)
        candidates.append((ports.config_port, ports.data_port))
        if ports.config_port != ports.data_port:
            candidates.append((ports.data_port, ports.config_port))

    errors: list[str] = []
    chosen: Optional[tuple[str, str]] = None
    for cfg, dat in candidates:
        alive = False
        try:
            serial_mgr.connect(cfg, dat)
            alive, probe_rsp = serial_mgr.probe_cli(timeout_s=1.0)
            if alive:
                chosen = (cfg, dat)
                break
            errors.append(f"{cfg}/{dat}: CLI did not respond")
            logging.getLogger("capture_all_sensors_rich").warning(
                "CLI probe failed for config/data %s/%s. response='%s'",
                cfg,
                dat,
                (probe_rsp or "").strip()[:160],
            )
        except Exception as exc:
            errors.append(f"{cfg}/{dat}: {exc}")
        finally:
            if alive:
                continue
            if not serial_mgr.is_connected:
                continue
            try:
                serial_mgr.disconnect()
            except Exception:
                pass
    if chosen is not None:
        return chosen
    raise RuntimeError(
        "Failed to establish responsive mmWave CLI/DATA ports. "
        f"Tried pairs: {errors}. If issue persists, reconnect/reset sensor."
    )


def _point_to_dict(p: object) -> dict:
    if hasattr(p, "to_dict") and callable(p.to_dict):
        d = p.to_dict()
        return d if isinstance(d, dict) else {}
    return {
        "x": float(getattr(p, "x", 0.0)),
        "y": float(getattr(p, "y", 0.0)),
        "z": float(getattr(p, "z", 0.0)),
        "doppler": float(getattr(p, "doppler", 0.0)),
        "snr": float(getattr(p, "snr", 0.0)),
        "noise": float(getattr(p, "noise", 0.0)),
    }


def compute_risk_features(
    points: list[dict],
    persistent_buffer: deque[int],
    ema_prev: float,
    *,
    roi_half_width_m: float,
    roi_y_back_m: float,
    roi_y_front_m: float,
    snr_iqr_k: float,
    min_roi_points: int,
    persistent_threshold: float,
    persist_required: int,
    ema_alpha: float,
) -> tuple[dict, float]:
    # No points -> no ROI / no risk
    if not points:
        persistent_buffer.append(0)
        n_active = int(sum(persistent_buffer))
        ema = (1.0 - ema_alpha) * ema_prev
        return (
            {
                "centroid": None,
                "torso_roi": {
                    "x_min": None,
                    "x_max": None,
                    "y_min": None,
                    "y_max": None,
                    "point_count": 0,
                },
                "reflective_fraction": 0.0,
                "reflective_fraction_ema": float(ema),
                "persistence": {
                    "window": int(len(persistent_buffer)),
                    "active_count": n_active,
                    "required_count": int(persist_required),
                    "is_persistent": bool(n_active >= persist_required),
                },
                "risk_score_mmwave": float(min(1.0, max(0.0, ema))),
            },
            float(ema),
        )

    xs = [float(p.get("x", 0.0)) for p in points]
    ys = [float(p.get("y", 0.0)) for p in points]
    cx = float(np.median(xs))
    cy = float(np.median(ys))

    x_min, x_max = cx - roi_half_width_m, cx + roi_half_width_m
    y_min, y_max = cy - roi_y_back_m, cy + roi_y_front_m

    roi_points = [p for p in points if x_min <= float(p.get("x", 0.0)) <= x_max and y_min <= float(p.get("y", 0.0)) <= y_max]
    roi_snrs = [float(p.get("snr", 0.0)) for p in roi_points]

    reflective_fraction = 0.0
    if len(roi_snrs) >= min_roi_points:
        snr_med = float(np.median(roi_snrs))
        q1 = float(np.percentile(roi_snrs, 25))
        q3 = float(np.percentile(roi_snrs, 75))
        iqr = max(1e-6, q3 - q1)
        thr = snr_med + snr_iqr_k * iqr
        n_ref = sum(1 for s in roi_snrs if s > thr)
        reflective_fraction = n_ref / max(1, len(roi_snrs))

    active = int(reflective_fraction >= persistent_threshold and len(roi_points) >= min_roi_points)
    persistent_buffer.append(active)
    n_active = int(sum(persistent_buffer))
    is_persistent = bool(n_active >= persist_required)

    ema = (1.0 - ema_alpha) * ema_prev + ema_alpha * reflective_fraction
    risk_score = min(1.0, max(0.0, 0.5 * ema + (0.5 if is_persistent else 0.0)))

    return (
        {
            "centroid": {"x": cx, "y": cy},
            "torso_roi": {
                "x_min": x_min,
                "x_max": x_max,
                "y_min": y_min,
                "y_max": y_max,
                "point_count": len(roi_points),
            },
            "reflective_fraction": float(reflective_fraction),
            "reflective_fraction_ema": float(ema),
            "persistence": {
                "window": int(len(persistent_buffer)),
                "active_count": n_active,
                "required_count": int(persist_required),
                "is_persistent": is_persistent,
            },
            "risk_score_mmwave": float(risk_score),
        },
        float(ema),
    )


def main() -> int:
    args = build_parser().parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger("capture_all_sensors_rich")

    cfg_path = resolve_config_path(args.config)
    if not args.skip_mmwave_config and not cfg_path.exists():
        raise RuntimeError(f"Config file not found: {cfg_path}")

    serial_mgr = SerialManager()
    thermal = None
    presence_source: Optional[PresenceSource] = None
    writer = None
    records: list[dict] = []

    p_hist: deque[float] = deque(maxlen=300)
    m_hist: deque[float] = deque(maxlen=300)
    persistent_buffer: deque[int] = deque(maxlen=max(1, int(args.persist_window)))
    risk_ema = 0.0

    try:
        used_cli_port, used_data_port = connect_mmwave_with_recovery(serial_mgr, args.cli_port, args.data_port)
        logger.info("Using mmWave ports CLI=%s DATA=%s", used_cli_port, used_data_port)
        if not args.skip_mmwave_config:
            cfg_result = RadarConfigurator(serial_mgr).configure_from_file(cfg_path)
            if not cfg_result.success:
                raise RuntimeError(f"mmWave config failed: {cfg_result.errors[:5]}")

        src = UARTSource(serial_mgr)
        parser = TLVParser()
        serial_mgr.flush_data_port()
        src.clear_buffer()

        thermal = ThermalCameraSource(
            device=args.thermal_device,
            width=args.thermal_width,
            height=args.thermal_height,
            fps=args.thermal_fps,
        )

        try:
            presence_source = build_presence_source(args.presence, args.ifx_uuid)
        except Exception as exc:
            logger.warning("Infineon init failed, disabling presence stream: %s", exc)
            presence_source = None

        panel_w = int(args.panel_width)
        panel_h = int(args.panel_height)
        out_w = panel_w * 3
        out_h = panel_h
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.video, fourcc, max(1.0, 1.0 / max(args.interval_s, 0.01)), (out_w, out_h))
        if not writer.isOpened():
            raise RuntimeError(f"Could not open video writer: {args.video}")

        started = time.time()
        for i in range(args.frames):
            t_ms = time.time() * 1000.0

            mmw_parsed = None
            raw = src.read_frame(timeout_ms=args.mmwave_timeout_ms)
            if raw is not None:
                mmw_parsed = parser.parse(raw)

            prs = None
            if presence_source is not None:
                try:
                    prs = presence_source.read_frame()
                    p_hist.append(float(prs.presence_raw))
                    m_hist.append(float(prs.motion_raw))
                except Exception as exc:
                    logger.debug("Presence read failed: %s", exc)

            thermal_bgr = thermal.read_colormap_bgr() if thermal is not None else None
            if thermal_bgr is None:
                thermal_bgr = np.zeros((panel_h, panel_w, 3), dtype=np.uint8)
            else:
                thermal_bgr = cv2.resize(thermal_bgr, (panel_w, panel_h), interpolation=cv2.INTER_LINEAR)
            cv2.putText(thermal_bgr, "Thermal", (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

            radar_panel = render_radar_panel(panel_w, panel_h, mmw_parsed)
            inf_panel = render_infineon_panel(panel_w, panel_h, p_hist, m_hist)
            combined = np.hstack((thermal_bgr, radar_panel, inf_panel))
            writer.write(combined)

            mmw_points_obj = list(getattr(mmw_parsed, "points", []) or [])
            mmw_points = [_point_to_dict(p) for p in mmw_points_obj]
            risk_features, risk_ema = compute_risk_features(
                mmw_points,
                persistent_buffer,
                risk_ema,
                roi_half_width_m=float(args.roi_half_width_m),
                roi_y_back_m=float(args.roi_y_back_m),
                roi_y_front_m=float(args.roi_y_front_m),
                snr_iqr_k=float(args.snr_iqr_k),
                min_roi_points=int(args.min_roi_points),
                persistent_threshold=float(args.persistent_threshold),
                persist_required=int(args.persist_required),
                ema_alpha=float(args.ema_alpha),
            )

            rec = {
                "index": i,
                "timestamp_ms": t_ms,
                "mmwave": {
                    "frame_number": getattr(mmw_parsed, "frame_number", None),
                    "num_points": len(mmw_points),
                    "points": mmw_points,
                    "risk_features": risk_features,
                },
                "presence": None
                if prs is None
                else {
                    "frame_number": prs.frame_number,
                    "presence_raw": float(prs.presence_raw),
                    "motion_raw": float(prs.motion_raw),
                    "distance_m": None if float(prs.distance_m) < 0 else float(prs.distance_m),
                },
                "thermal": {
                    "mean_u8": float(np.mean(cv2.cvtColor(thermal_bgr, cv2.COLOR_BGR2GRAY))),
                    "shape": list(thermal_bgr.shape),
                },
            }
            records.append(rec)

            elapsed = time.time() - started
            fps = (i + 1) / elapsed if elapsed > 0 else 0.0
            print(f"\rFrame {i + 1}/{args.frames} | FPS {fps:.2f} | mmRisk {risk_features['risk_score_mmwave']:.2f}", end="")
            if args.interval_s > 0:
                time.sleep(args.interval_s)

        print()
        out_json = Path(args.output).expanduser().resolve()
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with out_json.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "capture_info": {
                        "frames": len(records),
                        "duration_s": time.time() - started,
                        "video": str(Path(args.video).resolve()),
                        "risk_params": {
                            "roi_half_width_m": float(args.roi_half_width_m),
                            "roi_y_back_m": float(args.roi_y_back_m),
                            "roi_y_front_m": float(args.roi_y_front_m),
                            "snr_iqr_k": float(args.snr_iqr_k),
                            "min_roi_points": int(args.min_roi_points),
                            "persistent_threshold": float(args.persistent_threshold),
                            "persist_window": int(args.persist_window),
                            "persist_required": int(args.persist_required),
                            "ema_alpha": float(args.ema_alpha),
                        },
                    },
                    "frames": records,
                },
                f,
                indent=2,
            )

        print(f"Saved video: {Path(args.video).resolve()}")
        print(f"Saved json : {out_json}")
        return 0
    finally:
        if writer is not None:
            try:
                writer.release()
            except Exception:
                pass
        if thermal is not None:
            try:
                thermal.close()
            except Exception:
                pass
        if presence_source is not None:
            provider = getattr(presence_source, "_provider", None)
            close_fn = getattr(provider, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    pass
        if serial_mgr.is_connected:
            try:
                RadarConfigurator(serial_mgr).stop()
            except Exception:
                pass
            try:
                serial_mgr.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())

