#!/usr/bin/env python3
"""Load training samples and build feature matrix + labels for AI training.

Usage::

    # Show dataset summary
    python -m layer1_sensor_hub.mmwave_dca.train_data_loader \\
        --summary

    # Export numpy arrays for sklearn / pytorch
    python -m layer1_sensor_hub.mmwave_dca.train_data_loader \\
        --export /tmp/training_data.npz
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

# feature names (in order, matches MultiModalFeatures.to_vector())
FEATURE_NAMES = [
    "zone_coherence_max", "coherence_contrast",
    "zone_phase_stability", "pstab_contrast",
    "zone_energy_ratio", "n_cfar_detections_zone",
    "n_cfar_detections_total", "motion_energy",
    "mmwave_weapon_score",
    "n_points_total", "n_points_zone",
    "mean_snr", "max_snr", "range_spread",
    "rgb_mean_brightness", "rgb_std_brightness",
    "rgb_motion_magnitude", "rgb_green_dominant",
    "rgb_skin_pct", "rgb_waist_region_brightness",
    "thermal_mean", "thermal_std",
    "thermal_max", "thermal_min",
    "thermal_body_heat_pct", "thermal_cold_spot_pct",
    "thermal_waist_region_heat",
    "mmwave_thermal_corr", "any_sensor_active",
]

HERE = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = HERE / "data" / "training"


def load_samples(data_dir: str | Path) -> list[dict]:
    data_dir = Path(data_dir)
    samples = []
    for session_dir in sorted(data_dir.iterdir()):
        if not session_dir.is_dir():
            continue
        meta_path = session_dir / "metadata.json"
        npz_path = session_dir / "features.npz"
        if not meta_path.exists() or not npz_path.exists():
            continue
        with open(meta_path) as f:
            meta = json.load(f)
        npz = np.load(npz_path)
        samples.append({
            "session": session_dir.name,
            "meta": meta,
            "features": npz["feature_vectors"],  # [n_frames, 29]
            "scores": npz["scores"],
            "label": npz["label"][0],
        })
    return samples


def build_training_matrix(
    samples: list[dict],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    X_list = []
    y_list = []
    labels = []
    for s in samples:
        # Average features across frames for a session-level vector
        X_list.append(s["features"].mean(axis=0))
        y_list.append(s["label"])
        labels.append(s["session"])
    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.float32), labels


def main() -> int:
    p = argparse.ArgumentParser(description="Load and export training samples")
    p.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    p.add_argument("--summary", action="store_true", help="Show dataset summary")
    p.add_argument("--export", default="", help="Export NPZ path")
    args = p.parse_args()

    samples = load_samples(args.data_dir)
    if not samples:
        print(f"No training samples found in {args.data_dir}")
        return 1

    X, y, labels = build_training_matrix(samples)

    if args.summary:
        print(f"Training samples: {len(samples)}")
        print(f"  Feature vector: {X.shape[1]} dims")
        print(f"  Total frames: {sum(s['features'].shape[0] for s in samples)}")
        n_weapon = sum(1 for s in samples if s["label"] > 0.5)
        n_no_weapon = len(samples) - n_weapon
        print(f"  weapon: {n_weapon}  no_weapon: {n_no_weapon}")
        print()
        for s, x, lbl in zip(samples, X, labels):
            print(f"  {s['session']:40s} label={'weapon' if s['label'] else 'no_weapon':10s}  "
                  f"score={s['meta']['score_mean']:.4f}")

    if args.export:
        np.savez(args.export, X=X, y=y, labels=labels)
        print(f"Exported: {args.export}  X={X.shape} y={y.shape}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
