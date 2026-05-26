#!/usr/bin/env python3
"""Body-scan point cloud visualization — scan people, detect hidden weapons.

Two panels:
  Left:  Bird's-eye view (Range × Angle) — all detections
  Right: Doppler-Range view — weapon zone highlighted in red

Body points are blue, weapon-zone points are red.
Weapon score is shown as a badge in the corner.

Usage::

    python -m layer1_sensor_hub.mmwave_dca.visualize_pointcloud \\
        data/point_clouds/weapon_1m.csv -o body_scan.png
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def main():
    p = argparse.ArgumentParser(
        description="Body-scan radar point cloud — find concealed weapons"
    )
    p.add_argument("csv", help="Point cloud CSV (5+ cols: frame,range,doppler,angle,snr,zone_flag)")
    p.add_argument("--max-points", type=int, default=5000)
    p.add_argument("--score", type=float, default=None,
                   help="Weapon score to display (overrides mean)")
    p.add_argument("--output", "-o", default="", help="Save PNG")
    p.add_argument("--title", default="", help="Plot title")
    args = p.parse_args()

    data = np.loadtxt(args.csv, delimiter=",", skiprows=1)
    if data.ndim != 2 or data.shape[1] < 5:
        print(f"error: expected 5+ columns, got shape {data.shape}")
        return 1

    rng = data[:, 1] * 0.013
    dop = data[:, 2]
    ang = data[:, 3]
    snr = data[:, 4]
    zone = data[:, 5].astype(bool) if data.shape[1] >= 6 else np.zeros(len(data), dtype=bool)

    n = min(len(data), args.max_points)
    if n < len(data):
        idx = np.random.choice(len(data), n, replace=False)
        rng, dop, ang, snr, zone = rng[idx], dop[idx], ang[idx], snr[idx], zone[idx]

    score = args.score if args.score is not None else float(np.mean(snr))

    fig = plt.figure(figsize=(16, 7))

    # --- Bird's-eye view (Range × Angle) ---
    ax1 = fig.add_subplot(121)
    ax1.scatter(rng[~zone], ang[~zone], c="#2196F3", alpha=0.5, s=10, label="Body", edgecolors="none")
    ax1.scatter(rng[zone], ang[zone], c="#F44336", alpha=0.9, s=28, label="Weapon zone", edgecolors="white", linewidths=0.5)
    ax1.set_xlabel("Range (m)", fontsize=12)
    ax1.set_ylabel("Angle (rad)", fontsize=12)
    ax1.set_title("Bird's-Eye View", fontsize=13, fontweight="bold")
    ax1.grid(True, alpha=0.25)
    ax1.set_facecolor("#f0f2f5")
    ax1.legend(fontsize=10, loc="upper right")
    # Shade weapon zone
    ax1.axvspan(1.17, 1.95, color="red", alpha=0.06, label="Weapon zone range")
    ax1.set_xlim(0.5, 3.0)
    ax1.set_ylim(-0.8, 0.8)

    # --- Body scan view (Range × Doppler, colored by body vs weapon) ---
    ax2 = fig.add_subplot(122)
    ax2.scatter(rng[~zone], dop[~zone], c="#2196F3", alpha=0.5, s=10, label="Body", edgecolors="none")
    ax2.scatter(rng[zone], dop[zone], c="#F44336", alpha=0.9, s=28, label="Weapon zone", edgecolors="white", linewidths=0.5)
    ax2.set_xlabel("Range (m)", fontsize=12)
    ax2.set_ylabel("Doppler bin", fontsize=12)
    ax2.set_title("Doppler–Range Scan", fontsize=13, fontweight="bold")
    ax2.grid(True, alpha=0.25)
    ax2.set_facecolor("#f0f2f5")
    ax2.axvspan(1.17, 1.95, color="red", alpha=0.06)
    ax2.set_xlim(0.5, 3.0)
    ax2.set_ylim(0, 16)

    # Weapon score badge
    score_color = "#4CAF50" if score >= 0.65 else "#FF9800"
    fig.text(0.88, 0.92, f"WEAPON SCORE", fontsize=9, ha="center", color="gray",
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.8))
    fig.text(0.88, 0.86, f"{score:.2f}", fontsize=24, ha="center", fontweight="bold", color=score_color)

    # Summary info
    n_body = int((~zone).sum())
    n_weapon = int(zone.sum())
    title = args.title or f"Radar Body Scan — {n_body + n_weapon} points  |  {n_weapon} in weapon zone"
    fig.suptitle(title, fontsize=14, y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.93])

    if args.output:
        plt.savefig(args.output, dpi=200, bbox_inches="tight")
        print(f"saved: {args.output}")
    else:
        plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
