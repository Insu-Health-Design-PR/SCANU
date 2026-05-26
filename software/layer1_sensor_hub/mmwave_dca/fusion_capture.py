#!/usr/bin/env python3
"""Sensor fusion: overlay radar point cloud on RGB + thermal + radar views.

Two modes:
  1. ``--bin`` — load existing ADC capture, take live camera frames, fuse
  2. ``--capture`` — take cameras FIRST, then run DCA1000 radar capture, fuse

Usage::

    # Mode 1: existing capture
    python -m layer1_sensor_hub.mmwave_dca.fusion_capture \\
        --bin captures/weapon_only_1m.bin --allow-truncate \\
        --output captures/fusion_result.png

    # Mode 2: live capture (person stays still for ~5 s)
    python -m layer1_sensor_hub.mmwave_dca.fusion_capture \\
        --capture --duration 4 \\
        --output captures/fusion_live.png
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

import os
import sys

import cv2
import numpy as np

from layer1_sensor_hub.mmwave_dca.adc_reader import AdcCaptureShape, read_adc_data
from layer1_sensor_hub.mmwave_dca.mmwave_raw_adc_detector import RawAdcWeaponDetector
from layer1_sensor_hub.thermal.thermal_source import ThermalCameraSource, normalize_thermal_frame


def capture_cameras(args) -> tuple[np.ndarray, np.ndarray]:
    rgb_img = np.zeros((args.rgb_height, args.rgb_width, 3), dtype=np.uint8)
    rgb_img[:] = (30, 30, 30)
    thermal_img = np.zeros((args.thermal_height, args.thermal_width, 3), dtype=np.uint8)
    thermal_img[:] = (30, 30, 30)

    print("Capturing cameras...")
    rgb_cap = cv2.VideoCapture(args.rgb_device, cv2.CAP_V4L2)
    if rgb_cap.isOpened():
        rgb_cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.rgb_width)
        rgb_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.rgb_height)
        rgb_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        for _ in range(5):
            rgb_cap.read()
        ok, frame = rgb_cap.read()
        if ok:
            rgb_img = cv2.resize(frame, (args.rgb_width, args.rgb_height))
            print(f"  RGB: {rgb_img.shape}")
        rgb_cap.release()
    else:
        print("  warning: RGB not available")

    try:
        thm = ThermalCameraSource(
            device=args.thermal_device,
            width=args.thermal_width,
            height=args.thermal_height,
            fps=9,
        )
        raw = thm.read_raw()
        if raw is not None:
            gray = normalize_thermal_frame(raw)
            thermal_img = cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)
            print(f"  Thermal: {thermal_img.shape}")
        thm.close()
    except Exception as e:
        print(f"  warning: thermal not available ({e})")

    return rgb_img, thermal_img


def project_radar_point(
    range_m: float, angle_rad: float,
    width: int, height: int,
    x_scale: float, y_scale: float,
    x_offset: float, y_offset: float,
    rotation_deg: float,
) -> tuple[int, int]:
    theta = np.radians(rotation_deg)
    x = range_m * np.sin(angle_rad)
    y = range_m * np.cos(angle_rad)
    xr = x * np.cos(theta) - y * np.sin(theta)
    yr = x * np.sin(theta) + y * np.cos(theta)
    u = width // 2 + x_offset + int(xr * x_scale)
    v = height - y_offset - int(yr * y_scale)
    return int(np.clip(u, 0, width - 1)), int(np.clip(v, 0, height - 1))


def draw_point_cloud_on_image(
    img: np.ndarray,
    points: np.ndarray,
    width: int, height: int,
    x_scale: float, y_scale: float,
    x_offset: float, y_offset: float,
    rotation_deg: float,
):
    for pt in points:
        rng_m = pt[1] * 0.013
        ang = pt[3]
        zone = pt[5] if len(pt) >= 6 else 0.0
        color = (0, 0, 255) if zone > 0.5 else (255, 180, 0)
        u, v = project_radar_point(rng_m, ang, width, height,
                                   x_scale, y_scale, x_offset, y_offset, rotation_deg)
        if zone > 0.5:
            cv2.circle(img, (u, v), 8, color, -1)
            cv2.circle(img, (u, v), 8, (255, 255, 255), 1)
        else:
            cv2.circle(img, (u, v), 4, color, -1)


def main():
    p = argparse.ArgumentParser(description="Radar + RGB + Thermal fusion capture")
    p.add_argument("--bin", default="", help="ADC .bin file to process (omit for live capture)")
    p.add_argument("--capture", action="store_true", help="Live capture mode: cameras then radar")
    p.add_argument("--duration", type=int, default=4, help="Duration in seconds for live capture")
    p.add_argument("--chirps", type=int, default=16)
    p.add_argument("--rx", type=int, default=4)
    p.add_argument("--samples", type=int, default=384)
    p.add_argument("--allow-truncate", action="store_true")
    p.add_argument("--output", "-o", default="fusion_result.png")

    # DCA1000 config for live capture
    p.add_argument("--cli-port", default="/dev/ttyUSB0", help="Radar CLI port")
    p.add_argument("--dca-config", default="",
                   help="DCA1000 JSON config (default: ti_cli/configFile.json)")

    # Camera calibration
    p.add_argument("--rgb-device", type=int, default=0, help="RGB camera V4L2 index")
    p.add_argument("--thermal-device", type=int, default=2, help="Thermal camera V4L2 index")
    p.add_argument("--rgb-width", type=int, default=1280)
    p.add_argument("--rgb-height", type=int, default=720)
    p.add_argument("--thermal-width", type=int, default=160)
    p.add_argument("--thermal-height", type=int, default=120)

    # Projection params (tune these for your setup)
    p.add_argument("--x-scale", type=float, default=300.0, help="Pixels per meter horizontally")
    p.add_argument("--y-scale", type=float, default=200.0, help="Pixels per meter vertically")
    p.add_argument("--x-offset", type=float, default=0.0, help="Horizontal offset px")
    p.add_argument("--y-offset", type=float, default=50.0, help="Vertical offset px (camera above radar)")
    p.add_argument("--rotation", type=float, default=0.0, help="Camera rotation deg")

    args = p.parse_args()

    software = Path(__file__).resolve().parent.parent.parent

    # --- Step 0: Live capture mode ---
    if args.capture or not args.bin:
        if not args.dca_config:
            args.dca_config = str(software / "layer1_sensor_hub" / "mmwave_dca" / "ti_cli" / "configFile.json")
        out_bin = f"/tmp/fusion_live_{int(time.time())}.bin"

        # Take camera photos FIRST (before radar capture)
        rgb_img, thermal_img = capture_cameras(args)

        print(f"Radar capture ({args.duration}s)... person stay still!")
        cfg = f"{software}/layer1_sensor_hub/testing/configs/weapon_detection_dca1000.cfg"
        mod = "layer1_sensor_hub.mmwave_dca.run_dca_capture"
        env = {**os.environ, "PYTHONPATH": str(software)}
        subprocess.run(
            [sys.executable, "-m", mod,
             "--cli-port", args.cli_port,
             "--config", cfg,
             "--dca-config", args.dca_config,
             "--output", out_bin,
             "--duration-s", str(args.duration),
             "--configure-dca", "--start-dca", "--stop-dca"],
            cwd=str(software), env=env,
        )
        args.allow_truncate = True
        args.bin = out_bin
    else:
        rgb_img, thermal_img = capture_cameras(args)

    # --- Step 1: Load radar data and process ---
    bin_path = Path(args.bin)
    if not bin_path.exists():
        print(f"error: {args.bin} not found")
        return 1
    nbytes = bin_path.stat().st_size
    frames = nbytes // (4 * args.chirps * args.rx * args.samples)
    shape = AdcCaptureShape(frames=frames, chirps=args.chirps, rx=args.rx, samples=args.samples)
    print(f"Loading ADC: {bin_path.name} ({frames} frames)")
    adc = read_adc_data(bin_path, shape, allow_truncate=args.allow_truncate)
    n_frames = min(30, adc.shape[0])

    detector = RawAdcWeaponDetector()
    cloud_points = []
    total_score = 0.0
    for i in range(n_frames):
        result = detector.detect(adc[i], i)
        total_score += result.weapon_score
        if result.point_cloud is not None:
            for pt in result.point_cloud:
                cloud_points.append(np.append(pt, [result.weapon_score]))
    cloud_points = np.array(cloud_points, dtype=np.float32) if cloud_points else np.empty((0, 6))
    mean_score = total_score / n_frames
    print(f"  Weapon score: {mean_score:.3f}  Cloud points: {len(cloud_points)}")

    # --- Step 2: Overlay radar points on camera images ---
    if len(cloud_points) > 0:
        # Sub-sample to avoid clutter
        n_show = min(500, len(cloud_points))
        idx = np.random.choice(len(cloud_points), n_show, replace=False)

        draw_point_cloud_on_image(
            rgb_img, cloud_points[idx],
            args.rgb_width, args.rgb_height,
            args.x_scale, args.y_scale,
            args.x_offset, args.y_offset, args.rotation,
        )

        thm_scale = args.x_scale * args.thermal_width / args.rgb_width
        thm_y_scale = args.y_scale * args.thermal_height / args.rgb_height
        thm_x_off = args.x_offset * args.thermal_width / args.rgb_width
        thm_y_off = args.y_offset * args.thermal_height / args.rgb_height
        draw_point_cloud_on_image(
            thermal_img, cloud_points[idx],
            args.thermal_width, args.thermal_height,
            thm_scale, thm_y_scale,
            thm_x_off, thm_y_off, args.rotation,
        )

    # 4. Build composite
    rgb_small = cv2.resize(rgb_img, (640, 360))
    thm_large = cv2.resize(thermal_img, (640, 480))

    # --- Radar top-down view ---
    radar_view = np.zeros((480, 640, 3), dtype=np.uint8)
    radar_view[:] = (10, 12, 16)
    if len(cloud_points) > 0:
        for pt in cloud_points:
            rng_m = pt[1] * 0.013
            ang = pt[3]
            zone = pt[5]
            x_px = int(320 + rng_m * 80 * np.sin(ang))
            y_px = int(460 - rng_m * 80 * np.cos(ang))
            color = (0, 0, 255) if zone > 0.5 else (255, 180, 0)
            cv2.circle(radar_view, (x_px, y_px), 3, color, -1)
        cv2.putText(radar_view, f"Weapon Score: {mean_score:.2f}", (12, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        # Range rings
        for r in range(1, 6):
            radius = int(r * 80)
            cv2.circle(radar_view, (320, 460), radius, (66, 49, 42), 1)
            cv2.putText(radar_view, f"{r}m", (320 + radius - 10, 460 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (168, 149, 139), 1)

    # Composite layout: 3 columns
    h1, w1 = rgb_small.shape[:2]
    h2, w2 = thm_large.shape[:2]
    h3, w3 = radar_view.shape[:2]
    composite_h = h1 + h2
    composite_w = max(w1 + w2, w3)
    composite = np.zeros((composite_h + h3 + 10, composite_w + 10, 3), dtype=np.uint8)
    composite[:] = (20, 20, 20)

    # Place RGB top-left
    composite[5:5+h1, 5:5+w1] = rgb_small
    cv2.putText(composite, "RGB + Radar Overlay", (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # Place Thermal top-right
    composite[5:5+h2, 10+w1:10+w1+w2] = thm_large
    cv2.putText(composite, "Thermal + Radar Overlay", (15 + w1, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # Place Radar bottom
    y_off = 10 + max(h1, h2)
    composite[y_off:y_off+h3, composite_w//2 - w3//2:composite_w//2 + w3//2 + w3%2] = radar_view
    cv2.putText(composite, "Radar Top-Down", (composite_w//2 - 60, y_off + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # Score badge
    score_color = (0, 200, 0) if mean_score >= 0.65 else (0, 165, 255)
    cv2.putText(composite, f"WEAPON: {mean_score:.2f}", (composite_w - 200, composite_h + h3 - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, score_color, 2, cv2.LINE_AA)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), composite, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    raise SystemExit(main())
