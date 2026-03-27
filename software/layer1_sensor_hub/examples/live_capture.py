"""
Capture radar frames and save visualization as video.

Usage:
python capture_frames.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config configs/full_config.cfg \
  --frames 300 \
  --video radar_output.mp4
"""

import argparse
import logging
import json
import sys
import time
import numpy as np
from pathlib import Path
from collections import deque

import cv2
import matplotlib.pyplot as plt

# Allow running this file directly without installing packages.
# - Add repo root so `software.*` imports work
# - Add `software/` so `layer1_radar` imports work
_repo_root = Path(__file__).resolve().parents[3]  # .../SCANU
_software_root = _repo_root / "software"
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_software_root))

from software.layer1_sensor_hub.mmwave import (
    SerialManager,
    RadarConfigurator,
    UARTSource,
    TLVParser,
)
from software.layer1_sensor_hub.thermal import ThermalCameraSource
from software.layer1_sensor_hub.mmwave import RadarPointFilterConfig, filter_detected_points


def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def assign_cluster_ids(points_xy: np.ndarray, radius_m: float = 0.75) -> np.ndarray:
    """
    Assign lightweight cluster ids using proximity in x/y.

    This is intentionally simple (no external deps) and runs per-frame.
    """
    n = points_xy.shape[0]
    if n == 0:
        return np.zeros((0,), dtype=np.int32)

    labels = np.full((n,), -1, dtype=np.int32)
    cluster_id = 0

    for i in range(n):
        if labels[i] != -1:
            continue

        labels[i] = cluster_id
        queue = [i]

        while queue:
            idx = queue.pop()
            # Broadcast distance check from current point to all points.
            d = points_xy - points_xy[idx]
            dist = np.sqrt(np.sum(d * d, axis=1))
            neighbors = np.where((dist <= radius_m) & (labels == -1))[0]
            if neighbors.size > 0:
                labels[neighbors] = cluster_id
                queue.extend(neighbors.tolist())

        cluster_id += 1

    return labels


def render_infineon_panel(
    width: int,
    height: int,
    presence_hist: "deque[float]",
    motion_hist: "deque[float]",
) -> np.ndarray:
    """
    Render a simple headless-safe panel for Infineon presence/motion.

    presence_hist: raw power-like value (float)
    motion_hist  : 0.0/1.0 motion flag
    """
    panel = np.zeros((height, width, 3), dtype=np.uint8)

    cv2.putText(panel, "Infineon (LTR11)", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    if len(presence_hist) == 0:
        cv2.putText(panel, "No data", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        return panel

    p = np.asarray(presence_hist, dtype=np.float32)
    m = np.asarray(motion_hist, dtype=np.float32) if len(motion_hist) == len(presence_hist) else None

    # Autoscale using a robust max to avoid one spike flattening everything.
    p_max = float(np.percentile(p, 98)) if p.size >= 5 else float(np.max(p))
    p_max = max(p_max, 1e-6)
    p_norm = np.clip(p / p_max, 0.0, 1.0)

    left = 10
    right = width - 10
    top = 80
    bottom = height - 20

    cv2.rectangle(panel, (left, top), (right, bottom), (60, 60, 60), 1)

    n = p_norm.size
    xs = np.linspace(left, right, n, dtype=np.int32)
    ys = (bottom - (p_norm * (bottom - top))).astype(np.int32)
    pts = np.column_stack([xs, ys]).reshape((-1, 1, 2))
    cv2.polylines(panel, [pts], isClosed=False, color=(0, 200, 255), thickness=2)

    cur_presence = float(p[-1])
    cur_motion = float(m[-1]) if m is not None and m.size > 0 else 0.0

    cv2.putText(
        panel,
        f"motion_energy: {cur_presence:.6f}",
        (10, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
    )

    motion_color = (0, 255, 0) if cur_motion >= 0.5 else (80, 80, 80)
    cv2.circle(panel, (right - 20, 52), 10, motion_color, -1)
    cv2.putText(panel, "motion", (right - 95, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 2)

    return panel


def main():
    parser = argparse.ArgumentParser(description="Radar capture with video output")

    parser.add_argument("--frames", "-n", type=int, default=300,
                        help="Number of frames (~300 = 30 sec @10FPS)")
    parser.add_argument("--config", "-c", required=True,
                        help="Path to FULL radar config file")
    parser.add_argument("--cli-port", required=True)
    parser.add_argument("--data-port", required=True)
    parser.add_argument("--video", "-vout", default="radar_output.mp4",
                        help="Output video file")
    parser.add_argument("--output", "-o", default=None,
                        help="Optional JSON output")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--cluster-radius",
        type=float,
        default=0.75,
        help="XY proximity radius in meters for per-frame color clusters",
    )
    parser.add_argument(
        "--render-mode",
        choices=["shape", "doppler", "snr"],
        default="shape",
        help=(
            "shape=single color cloud (best for person outline feel), "
            "doppler=color by signed velocity, snr=color by SNR"
        ),
    )
    parser.add_argument(
        "--weapon-overlay",
        action="store_true",
        help=(
            "Overlay high-motion points in red as a coarse cue. "
            "This is NOT true weapon detection."
        ),
    )
    parser.add_argument(
        "--weapon-doppler-thresh",
        type=float,
        default=0.45,
        help="Absolute doppler threshold (m/s) for red overlay points",
    )
    parser.add_argument("--thermal-device", type=int, default=0,
                        help="Thermal camera device index (default: /dev/video0)")
    parser.add_argument("--thermal-width", type=int, default=640,
                        help="Requested thermal camera width")
    parser.add_argument("--thermal-height", type=int, default=480,
                        help="Requested thermal camera height")
    parser.add_argument("--thermal-fps", type=int, default=30,
                        help="Requested thermal camera FPS")
    parser.add_argument(
        "--infineon",
        action="store_true",
        help="Enable Infineon LTR11 side panel (requires ifxradarsdk installed).",
    )
    parser.add_argument(
        "--infineon-uuid",
        default=None,
        help="Optional Infineon board UUID (defaults to first detected).",
    )
    parser.add_argument(
        "--no-frame-timeout-s",
        type=float,
        default=0.0,
        help=(
            "Abort recording if no mmWave frames arrive for this many seconds. "
            "Set 0 to disable (default)."
        ),
    )
    parser.add_argument("--mmw-min-range-m", type=float, default=0.35)
    parser.add_argument("--mmw-max-range-m", type=float, default=6.0)
    parser.add_argument("--mmw-max-azimuth-deg", type=float, default=65.0)
    parser.add_argument("--mmw-min-z-m", type=float, default=-1.0)
    parser.add_argument("--mmw-max-z-m", type=float, default=2.5)
    parser.add_argument("--mmw-min-snr-db", type=float, default=6.0)
    parser.add_argument("--mmw-max-abs-doppler-mps", type=float, default=6.0)

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    serial_mgr = SerialManager()
    thermal = None
    inf_provider = None
    video_writer = None
    fig = None
    point_filter_cfg = RadarPointFilterConfig(
        min_range_m=args.mmw_min_range_m,
        max_range_m=args.mmw_max_range_m,
        max_abs_azimuth_deg=args.mmw_max_azimuth_deg,
        min_z_m=args.mmw_min_z_m,
        max_z_m=args.mmw_max_z_m,
        min_snr_db=args.mmw_min_snr_db,
        max_abs_doppler_mps=args.mmw_max_abs_doppler_mps,
    )

    try:
        print("\n" + "="*60)
        print("Radar Capture + Video Recording")
        print("="*60)

        # 1. Connect
        print("\n[1/4] Connecting...")
        serial_mgr.connect(args.cli_port, args.data_port)
        print("Connected")

        # 2. Configure
        print("\n[2/4] Sending FULL config...")
        configurator = RadarConfigurator(serial_mgr)
        result = configurator.configure_from_file(Path(args.config))

        if not result.success:
            print("\nConfig FAILED:")
            for e in result.errors:
                print(f" - {e}")
            return

        print("Radar running")

        # 3. Setup video writer
        print("\n[3/4] Initializing video writer...")

        fps = 10  # matches your radar config (100ms frame)
        fig, ax = plt.subplots(figsize=(6.4, 4.8), dpi=100)

        # Base scatter for person-shape style view.
        scatter = ax.scatter([], [], c="deepskyblue", s=36, alpha=0.85)
        # Optional overlay to mark high-motion points (heuristic only).
        overlay_scatter = ax.scatter([], [], c="red", s=70, alpha=0.85, marker="x")

        ax.set_xlim(-5, 5)
        ax.set_ylim(0, 12)
        ax.set_xlabel("X (meters)")
        ax.set_ylabel("Y (meters)")
        ax.set_title("Radar Point Cloud")

        try:
            thermal = ThermalCameraSource(
                device=args.thermal_device,
                width=args.thermal_width,
                height=args.thermal_height,
                fps=args.thermal_fps,
            )
            thermal_info = thermal.info()
            print(f"Thermal camera: {thermal_info.width}x{thermal_info.height} @ {thermal_info.fps:.1f} FPS")
        except Exception as exc:
            thermal = None
            print(f"[warn] Thermal disabled (cannot open /dev/video{args.thermal_device}): {exc}")

        if args.infineon:
            # Lazy import so users without ifxradarsdk can still run mmWave+thermal.
            try:
                from software.layer1_sensor_hub.infeneon import IfxLtr11PresenceProvider

                inf_provider = IfxLtr11PresenceProvider(uuid=args.infineon_uuid)
                print("Infineon LTR11 enabled")
            except Exception as exc:
                inf_provider = None
                print(
                    "[warn] Infineon disabled (no device, bad SDK, or other init error): "
                    f"{exc}"
                )

        # Radar panel size from matplotlib figure canvas.
        fig.canvas.draw()
        radar_w, radar_h = fig.canvas.get_width_height()

        # Side-by-side output: thermal | mmWave radar | Infineon only if provider opened.
        panels = 3 if inf_provider is not None else 2
        out_w = radar_w * panels
        out_h = radar_h
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(args.video, fourcc, fps, (out_w, out_h))
        if not video_writer.isOpened():
            raise RuntimeError(f"Could not open output video writer: {args.video}")

        uart_source = UARTSource(serial_mgr)
        tlv_parser = TLVParser()

        inf_presence_hist: "deque[float]" = deque(maxlen=int(fps * 30))
        inf_motion_hist: "deque[float]" = deque(maxlen=int(fps * 30))

        serial_mgr.flush_data_port()
        uart_source.clear_buffer()

        frames_data = []
        start_time = time.time()
        last_frame_time = time.time()

        # 4. Capture loop
        print("\n[4/4] Recording video...\n")

        try:
            i = 0
            while i < args.frames:
                raw_frame = uart_source.read_frame(timeout_ms=300)
                if not raw_frame:
                    # Heartbeat + fail-fast when the data stream is dead.
                    now = time.time()
                    dt = now - last_frame_time
                    if float(args.no_frame_timeout_s) > 0 and dt >= float(args.no_frame_timeout_s):
                        raise RuntimeError(
                            f"No mmWave frames for {dt:.1f}s. "
                            f"Data port may be stalled. Try kill switch + re-run."
                        )
                    # Periodic progress line even when stalled.
                    if dt >= 1.0:
                        print(f"\rWaiting for mmWave frames... ({dt:.1f}s)", end="")
                    continue

                last_frame_time = time.time()
                parsed = tlv_parser.parse(raw_frame)
                raw_points = parsed.points
                points = filter_detected_points(raw_points, point_filter_cfg)

                x = [p.x for p in points]
                y = [p.y for p in points]
                doppler = [p.doppler for p in points]
                snr = [p.snr for p in points]

                # Update plot
                if len(x) > 0:
                    points_xy = np.column_stack((np.asarray(x), np.asarray(y)))
                    cluster_ids = assign_cluster_ids(points_xy, radius_m=args.cluster_radius)
                    num_objects = int(cluster_ids.max()) + 1

                    scatter.set_offsets(points_xy)
                    # Visual mode is independent from internal clustering.
                    if args.render_mode == "shape":
                        scatter.set_color("deepskyblue")
                        scatter.set_array(None)
                    elif args.render_mode == "doppler":
                        scatter.set_cmap("coolwarm")
                        scatter.set_clim(-1.0, 1.0)
                        scatter.set_array(np.asarray(doppler, dtype=np.float32))
                    else:  # snr
                        scatter.set_cmap("viridis")
                        scatter.set_clim(0.0, 35.0)
                        scatter.set_array(np.asarray(snr, dtype=np.float32))

                    if args.weapon_overlay:
                        dop = np.asarray(doppler, dtype=np.float32)
                        moving_idx = np.where(np.abs(dop) >= args.weapon_doppler_thresh)[0]
                        if moving_idx.size > 0:
                            overlay_scatter.set_offsets(points_xy[moving_idx])
                        else:
                            overlay_scatter.set_offsets(np.empty((0, 2)))
                    else:
                        overlay_scatter.set_offsets(np.empty((0, 2)))
                else:
                    scatter.set_offsets(np.empty((0, 2)))
                    scatter.set_array(np.array([], dtype=np.float32))
                    overlay_scatter.set_offsets(np.empty((0, 2)))
                    num_objects = 0

                # Capture frame into video
                fig.canvas.draw()
                radar_rgb = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
                radar_rgb = radar_rgb.reshape((radar_h, radar_w, 3))
                radar_bgr = cv2.cvtColor(radar_rgb, cv2.COLOR_RGB2BGR)

                if thermal is None:
                    thermal_bgr = np.zeros((radar_h, radar_w, 3), dtype=np.uint8)
                else:
                    thermal_bgr = thermal.read_colormap_bgr()
                    if thermal_bgr is None:
                        thermal_bgr = np.zeros((radar_h, radar_w, 3), dtype=np.uint8)
                    else:
                        thermal_bgr = cv2.resize(thermal_bgr, (radar_w, radar_h), interpolation=cv2.INTER_LINEAR)

                cv2.putText(thermal_bgr, "Thermal", (10, 24),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(radar_bgr, "Radar", (10, 24),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                inf_sample = None
                if inf_provider is not None:
                    try:
                        presence_raw, motion_raw, _distance_m = inf_provider.read_sample()
                        inf_presence_hist.append(float(presence_raw))
                        inf_motion_hist.append(float(motion_raw))
                        inf_sample = {
                            "presence_raw": float(presence_raw),
                            "motion_raw": float(motion_raw),
                        }
                    except Exception:
                        # Keep capture running even if Infineon read blips.
                        pass

                    inf_bgr = render_infineon_panel(
                        width=radar_w,
                        height=radar_h,
                        presence_hist=inf_presence_hist,
                        motion_hist=inf_motion_hist,
                    )
                    combined = np.hstack((thermal_bgr, radar_bgr, inf_bgr))
                else:
                    combined = np.hstack((thermal_bgr, radar_bgr))
                video_writer.write(combined)

                # Console output
                elapsed = time.time() - start_time
                fps_live = (i + 1) / elapsed if elapsed > 0 else 0

                print(f"\rFrame {i+1}/{args.frames} | "
                      f"Objects: {num_objects} | "
                      f"Points raw/filtered: {len(raw_points)}/{len(points)} | "
                      f"FPS: {fps_live:.1f}", end="")

                # Optional JSON
                if args.output:
                    thermal_mean = None
                    thermal_payload = None
                    if thermal is not None:
                        thermal_gray = cv2.cvtColor(thermal_bgr, cv2.COLOR_BGR2GRAY)
                        thermal_mean = float(np.mean(thermal_gray)) if thermal_gray.size else 0.0
                        thermal_payload = {
                            "mean_intensity_u8": thermal_mean,
                            "width": int(thermal_bgr.shape[1]),
                            "height": int(thermal_bgr.shape[0]),
                        }
                    frames_data.append({
                        "frame": parsed.frame_number,
                        "points_raw_count": len(raw_points),
                        "points_filtered_count": len(points),
                        "points": [p.to_dict() for p in points],
                        "thermal": thermal_payload,
                        "infineon": inf_sample,
                    })

                i += 1

        except KeyboardInterrupt:
            print("\nStopped by user")

        # Finish video
        video_writer.release()
        video_writer = None
        if thermal is not None:
            thermal.close()
            thermal = None
        plt.close(fig)
        fig = None

        print(f"\n\nVideo saved to: {args.video}")

        # Save JSON
        if args.output:
            with open(args.output, "w") as f:
                json.dump(frames_data, f, indent=2)
            print(f"JSON saved to: {args.output}")

        # NOTE: We intentionally do NOT send `sensorStop` here.
        # Closing the ports is usually enough, and repeated start/stop cycles
        # can leave some setups in a wedged state between runs.

    except Exception as e:
        logger.exception("Error")
        print(f"\nERROR: {e}")

    finally:
        if video_writer is not None:
            video_writer.release()
        if thermal is not None:
            thermal.close()
        if inf_provider is not None:
            try:
                inf_provider.close()
            except Exception:
                pass
        if fig is not None:
            plt.close(fig)
        serial_mgr.disconnect()
        print("Serial closed")


if __name__ == "__main__":
    main()
