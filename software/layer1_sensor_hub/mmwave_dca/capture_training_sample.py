#!/usr/bin/env python3
"""Capture synchronized multi-sensor training samples for AI model training.

Captures DCA1000 mmWave radar + RGB camera + thermal camera, processes
through the full detection pipeline, and saves a structured training
package in ``data/training/``.

Each capture produces::

    data/training/YYYYMMDD_HHMMSS_label/
        metadata.json         # timestamp, label, CLI args, scores
        adc_data.bin          # raw ADC capture (48 chirps)
        rgb_frame.jpg         # RGB camera (1280×720)
        thermal_frame.png     # thermal camera (16-bit PNG)
        features.npz          # arrays: feature_vector, label, scores, point_cloud
        point_cloud.csv       # [range, doppler, angle, snr, zone_flag]

Usage::

    # Live capture (sensors connected):
    python -m layer1_sensor_hub.mmwave_dca.capture_training_sample \\
        --label no_weapon --capture --duration 4

    # From existing ADC file + live cameras:
    python -m layer1_sensor_hub.mmwave_dca.capture_training_sample \\
        --bin captures/person_1m_weapon.bin --label weapon \\
        --allow-truncate
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from layer1_sensor_hub.mmwave_dca.adc_reader import AdcCaptureShape, read_adc_data
from layer1_sensor_hub.mmwave_dca.mmwave_raw_adc_detector import (
    MmweaponCfarParams,
    RawAdcWeaponDetector,
)
from layer3_features.multimodal_features import MultiModalFeatureExtractor

# ── paths ──────────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
TRAINING_DIR = DATA_DIR / "training"

# ── MIMO params ────────────────────────────────────────────────────────────
MIMO_CHIRPS = 48
LEGACY_CHIRPS = 16
RX = 4
SAMPLES = 384

# ── helpers ────────────────────────────────────────────────────────────────


def capture_rgb(
    device: int = 0,
    width: int = 1280,
    height: int = 720,
) -> np.ndarray:
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        print("  [warning] RGB camera not available")
        return np.zeros((height, width, 3), dtype=np.uint8)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    for _ in range(5):
        cap.read()
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return np.zeros((height, width, 3), dtype=np.uint8)
    return cv2.resize(frame, (width, height))


def capture_thermal(
    device: int = 2,
    width: int = 160,
    height: int = 120,
) -> np.ndarray:
    try:
        from layer1_sensor_hub.thermal.thermal_source import ThermalCameraSource

        thm = ThermalCameraSource(device=device, width=width, height=height, fps=9)
        raw = thm.read_raw()
        thm.close()
        if raw is not None:
            return raw.astype(np.uint16)
    except Exception as e:
        print(f"  [warning] thermal not available: {e}")
    return np.zeros((height, width), dtype=np.uint16)


def run_dca_capture(
    software_dir: Path,
    cli_port: str,
    dca_config: str,
    duration: int,
    out_path: str,
) -> bool:
    cfg = str(software_dir / "software" / "layer1_sensor_hub" / "testing" / "configs" / "weapon_detection_dca1000.cfg")
    mod = "layer1_sensor_hub.mmwave_dca.run_dca_capture"
    pythonpath = f"{str(software_dir / 'software')}:{str(software_dir)}"
    env = {**{"PYTHONPATH": pythonpath}, **{k: v for k, v in __import__("os").environ.items()}}
    result = subprocess.run(
        [sys.executable, "-m", mod,
         "--cli-port", cli_port,
         "--config", cfg,
         "--dca-config", dca_config,
         "--output", out_path,
         "--duration-s", str(duration),
         "--configure-dca", "--start-dca", "--stop-dca"],
        cwd=str(software_dir / "software"), env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  DCA1000 error: {result.stderr}")
        return False
    return True


# ── main ────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Capture synchronized multi-sensor training sample",
    )
    # Mode
    p.add_argument("--capture", action="store_true", help="Live capture mode")
    p.add_argument("--bin", default="", help="Existing ADC .bin file to process")
    p.add_argument("--label", default="unknown",
                   choices=["weapon", "no_weapon", "unknown", "other"],
                   help="Ground truth label for training")

    # Live capture options
    p.add_argument("--duration", type=int, default=4, help="Live capture duration (s)")
    p.add_argument("--cli-port", default="", help="Radar CLI port (auto-detect if empty)")
    p.add_argument("--dca-config", default="", help="DCA1000 JSON config path")
    p.add_argument("--allow-truncate", action="store_true", help="Allow truncated ADC files")

    # Camera devices
    p.add_argument("--rgb-device", type=int, default=0)
    p.add_argument("--thermal-device", type=int, default=2)
    p.add_argument("--rgb-width", type=int, default=1280)
    p.add_argument("--rgb-height", type=int, default=720)
    p.add_argument("--thermal-width", type=int, default=160)
    p.add_argument("--thermal-height", type=int, default=120)

    # Output
    p.add_argument("--outdir", default=str(TRAINING_DIR),
                   help="Output directory for training samples")

    return p


def main() -> int:
    args = build_parser().parse_args()
    software = HERE.parent.parent.parent

    if not args.dca_config:
        args.dca_config = str(software / "software" / "layer1_sensor_hub" / "mmwave_dca" / "ti_cli" / "configFile.json")

    if not args.cli_port:
        from .radar_cli import _find_cli_port
        detected = _find_cli_port()
        if detected is None:
            print("error: no radar CLI port found (try --cli-port)")
            return 1
        print(f"Auto-detected radar CLI port: {detected}")
        args.cli_port = detected

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # ── timestamp and session path ──────────────────────────────────────
    ts = time.strftime("%Y%m%d_%H%M%S")
    session = f"{ts}_{args.label}"
    session_dir = outdir / session
    session_dir.mkdir(parents=True, exist_ok=True)
    print(f"Session: {session_dir}")

    # ── Step 1: capture cameras ─────────────────────────────────────────
    print("Capturing cameras...")
    rgb_img = capture_rgb(args.rgb_device, args.rgb_width, args.rgb_height)
    thermal_img = capture_thermal(args.thermal_device, args.thermal_width, args.thermal_height)
    cv2.imwrite(str(session_dir / "rgb_frame.jpg"), rgb_img,
                [cv2.IMWRITE_JPEG_QUALITY, 95])
    cv2.imwrite(str(session_dir / "thermal_frame.png"), thermal_img,
                [cv2.IMWRITE_PNG_COMPRESSION, 3])
    print(f"  RGB: {rgb_img.shape}  Thermal: {thermal_img.shape}")

    # ── Step 2: capture or load radar data ──────────────────────────────
    if args.capture:
        print(f"Radar capture ({args.duration}s)...")
        bin_path = session_dir / "adc_data.bin"
        ok = run_dca_capture(
            software, args.cli_port, args.dca_config,
            args.duration, str(bin_path),
        )
        if not ok:
            print("error: DCA1000 capture failed")
            return 1
        allow_truncate = True
    elif args.bin:
        src = Path(args.bin)
        if not src.exists():
            print(f"error: {args.bin} not found")
            return 1
        bin_path = session_dir / "adc_data.bin"
        shutil.copy2(src, bin_path)
        print(f"Copied: {src.name} -> {bin_path}")
        allow_truncate = args.allow_truncate
    else:
        print("error: either --capture or --bin is required")
        return 1

    # ── Step 3: load and process ADC data ───────────────────────────────
    nbytes = bin_path.stat().st_size

    # Try MIMO first (48 chirps), fall back to legacy (16)
    n_frames_mimo = nbytes // (2 * MIMO_CHIRPS * RX * SAMPLES * 2)
    n_frames_legacy = nbytes // (2 * LEGACY_CHIRPS * RX * SAMPLES * 2)

    if n_frames_mimo >= 1:
        chirps = MIMO_CHIRPS
        n_frames = n_frames_mimo
        mimo_mode = True
    else:
        chirps = LEGACY_CHIRPS
        n_frames = n_frames_legacy
        mimo_mode = False

    shape = AdcCaptureShape(frames=n_frames, chirps=chirps, rx=RX, samples=SAMPLES)
    print(f"Loading ADC: {nbytes} bytes, {n_frames} frames x {chirps} chirps (MIMO={mimo_mode})")
    adc = read_adc_data(bin_path, shape, allow_truncate=allow_truncate)

    # ── Step 4: run detector ────────────────────────────────────────────
    if mimo_mode:
        cfar = MmweaponCfarParams(threshold_scale=3.0, noise_floor_offset_db=1.5)
    else:
        cfar = MmweaponCfarParams()  # legacy defaults
    detector = RawAdcWeaponDetector(cfar=cfar)
    extractor = MultiModalFeatureExtractor()

    all_features: list[dict] = []
    all_clouds: list[np.ndarray] = []
    feature_vectors: list[np.ndarray] = []
    scores: list[float] = []

    for i in range(min(n_frames, 50)):
        result = detector.detect(adc[i], i)
        scores.append(result.weapon_score)
        mm_features = extractor.extract(mmwave_result=result)
        feature_vectors.append(mm_features.to_vector())
        all_features.append(result.features)
        if result.point_cloud is not None and len(result.point_cloud) > 0:
            all_clouds.append(result.point_cloud)

    mean_score = float(np.mean(scores)) if scores else 0.0
    max_score = float(np.max(scores)) if scores else 0.0
    std_score = float(np.std(scores)) if scores else 0.0

    # Combine point clouds across frames
    cloud_all = np.concatenate(all_clouds, axis=0) if all_clouds else np.empty((0, 5), dtype=np.float32)

    # Save point cloud CSV
    if len(cloud_all) > 0:
        header = "range_bin,doppler_bin,angle_deg,snr,zone_flag"
        np.savetxt(session_dir / "point_cloud.csv", cloud_all,
                   fmt="%.1f,%.0f,%.1f,%.1f,%.0f", header=header)
        print(f"  Point cloud: {len(cloud_all)} points saved")

    # Save features NPZ
    feat_arr = np.stack(feature_vectors, axis=0)  # [n_frames, 29]
    label_val = 1.0 if args.label == "weapon" else 0.0
    np.savez(
        session_dir / "features.npz",
        feature_vectors=feat_arr,
        scores=np.array(scores, dtype=np.float32),
        label=np.array([label_val], dtype=np.float32),
        label_str=args.label,
        frame_indices=np.arange(len(feature_vectors)),
    )
    print(f"  Features: {feat_arr.shape} saved")

    # Save metadata
    meta = {
        "session": session,
        "timestamp": ts,
        "label": args.label,
        "label_value": label_val,
        "mimo_mode": mimo_mode,
        "n_frames": n_frames,
        "n_frames_processed": len(feature_vectors),
        "chirps": chirps,
        "rx": RX,
        "samples": SAMPLES,
        "score_mean": mean_score,
        "score_max": max_score,
        "score_std": std_score,
        "n_point_cloud_points": len(cloud_all),
        "cfar_threshold_scale": cfar.threshold_scale,
        "cfar_noise_floor_offset_db": cfar.noise_floor_offset_db,
        "rgb_width": args.rgb_width,
        "rgb_height": args.rgb_height,
        "thermal_width": args.thermal_width,
        "thermal_height": args.thermal_height,
        "raw_bin_path": str(bin_path),
        "cli_args": vars(args),
    }
    with open(session_dir / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2, default=str)
    print(f"  Score: {mean_score:.4f} ± {std_score:.4f} (max {max_score:.4f})")
    print(f"  Saved: {session_dir}")
    print("Done.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
