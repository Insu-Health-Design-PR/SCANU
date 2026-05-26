#!/usr/bin/env python3
"""Plot point cloud CSV in academic paper style (bird's-eye + 3D).

Two views side-by-side:
  Left:  Bird's-eye view (Range vs Angle)  — like radar paper figures
  Right: 3D view (Range, Doppler, Angle)   — colored by SNR

Usage::

    python -m layer1_sensor_hub.mmwave_dca.visualize_pointcloud \\
        data/point_clouds/weapon_1m.csv -o pointcloud_paper.png
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize


def main():
    p = argparse.ArgumentParser(
        description="Radar point cloud visualization (paper-style)"
    )
    p.add_argument("csv", help="Path to point cloud CSV")
    p.add_argument("--max-points", type=int, default=3000, help="Max points to plot")
    p.add_argument("--output", "-o", default="", help="Save PNG (default: show window)")
    args = p.parse_args()

    data = np.loadtxt(args.csv, delimiter=",", skiprows=1)
    if data.ndim != 2 or data.shape[1] < 5:
        print(f"error: expected 5+ columns, got shape {data.shape}")
        return 1

    rng = data[:, 1] * 0.013
    dop = data[:, 2]
    ang = data[:, 3]
    snr = data[:, 4]

    n = min(len(data), args.max_points)
    idx = np.random.choice(len(data), n, replace=False) if n < len(data) else slice(None)
    rng, dop, ang, snr = rng[idx], dop[idx], ang[idx], snr[idx]

    cmap = "jet"
    norm = Normalize(vmin=snr.min(), vmax=snr.max())

    fig = plt.figure(figsize=(16, 7))
    fig.suptitle("Radar Point Cloud — mmWave DCA1000 + IWR6843", fontsize=14, y=0.98)

    # --- Left: Bird's-eye view (Range vs Angle) ---
    ax1 = fig.add_subplot(121)
    sc1 = ax1.scatter(rng, ang, c=snr, cmap=cmap, norm=norm, alpha=0.7, s=18, edgecolors="k", linewidths=0.3)
    ax1.set_xlabel("Range (m)", fontsize=12)
    ax1.set_ylabel("Angle (rad)", fontsize=12)
    ax1.set_title("Bird's-Eye View", fontsize=13, fontweight="bold")
    ax1.grid(True, alpha=0.3)
    ax1.set_facecolor("#f8f9fa")
    ax1.set_xlim(1.0, 2.2)

    # --- Right: 3D view (Range, Doppler, Angle) ---
    ax2 = fig.add_subplot(122, projection="3d")
    sc2 = ax2.scatter(rng, ang, dop, c=snr, cmap=cmap, norm=norm, alpha=0.7, s=14, edgecolors="k", linewidths=0.2)
    ax2.set_xlabel("Range (m)", fontsize=12, labelpad=8)
    ax2.set_ylabel("Angle (rad)", fontsize=12, labelpad=8)
    ax2.set_zlabel("Doppler bin", fontsize=12, labelpad=8)
    ax2.set_title("3D Point Cloud", fontsize=13, fontweight="bold")
    ax2.set_xlim(1.0, 2.2)
    ax2.set_ylim(-0.8, 0.8)
    ax2.set_zlim(0, 16)
    ax2.view_init(elev=25, azim=-60)

    # Shared colorbar
    cbar = fig.colorbar(sc2, ax=[ax1, ax2], shrink=0.6, pad=0.02)
    cbar.set_label("SNR (dB)", fontsize=11)

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    if args.output:
        plt.savefig(args.output, dpi=200, bbox_inches="tight")
        print(f"saved: {args.output}")
    else:
        plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
