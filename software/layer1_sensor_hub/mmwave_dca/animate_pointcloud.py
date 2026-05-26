#!/usr/bin/env python3
"""Animated body-scan point cloud — frame by frame, weapon zone highlighted.

Usage::

    python -m layer1_sensor_hub.mmwave_dca.animate_pointcloud \\
        data/point_clouds/fullscan_weapon.csv \\
        -o data/point_clouds/animation_body_scan.mp4
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter


def main():
    p = argparse.ArgumentParser(description="Animate body-scan point cloud frames")
    p.add_argument("csv", help="Point cloud CSV (6 cols: frame,range,doppler,angle,snr,zone_flag)")
    p.add_argument("--output", "-o", default="body_scan_animation.mp4")
    p.add_argument("--fps", type=int, default=8)
    p.add_argument("--max-points", type=int, default=300)
    args = p.parse_args()

    data = np.loadtxt(args.csv, delimiter=",", skiprows=1)
    if data.ndim != 2 or data.shape[1] < 5:
        print(f"error: expected 5+ columns, got shape {data.shape}")
        return 1

    has_zone = data.shape[1] >= 6

    frames_u = np.unique(data[:, 0]).astype(int)
    frames_u.sort()
    print(f"Loaded {len(data)} points across {len(frames_u)} frames")

    fig = plt.figure(figsize=(16, 7))

    n_show = min(len(frames_u), 100)
    step = max(1, len(frames_u) // n_show)

    writer = FFMpegWriter(fps=args.fps)
    with writer.saving(fig, args.output, dpi=150):
        for idx in range(0, len(frames_u), step):
            f = frames_u[idx]
            mask = data[:, 0] == f
            pts = data[mask]
            if len(pts) == 0:
                continue

            n_pts = min(len(pts), args.max_points)
            if n_pts < len(pts):
                sel = np.random.choice(len(pts), n_pts, replace=False)
                pts = pts[sel]

            rng = pts[:, 1] * 0.013
            dop = pts[:, 2]
            ang = pts[:, 3]
            zone = pts[:, 5].astype(bool) if has_zone else np.zeros(len(pts), dtype=bool)

            # --- Bird's-eye ---
            ax1 = fig.add_subplot(121)
            ax1.clear()
            ax1.scatter(rng[~zone], ang[~zone], c="#2196F3", alpha=0.5, s=10, label="Body")
            ax1.scatter(rng[zone], ang[zone], c="#F44336", alpha=0.9, s=28,
                        label="Weapon zone", edgecolors="white", linewidths=0.5)
            ax1.set_xlabel("Range (m)", fontsize=12)
            ax1.set_ylabel("Angle (rad)", fontsize=12)
            ax1.set_title(f"Bird's-Eye — frame {int(f)}", fontsize=12, fontweight="bold")
            ax1.grid(True, alpha=0.25)
            ax1.set_facecolor("#f0f2f5")
            ax1.axvspan(1.17, 1.95, color="red", alpha=0.06)
            ax1.set_xlim(0.5, 3.0)
            ax1.set_ylim(-0.8, 0.8)
            ax1.legend(fontsize=9, loc="upper right")

            # --- Doppler-Range ---
            ax2 = fig.add_subplot(122)
            ax2.clear()
            ax2.scatter(rng[~zone], dop[~zone], c="#2196F3", alpha=0.5, s=10, label="Body")
            ax2.scatter(rng[zone], dop[zone], c="#F44336", alpha=0.9, s=28,
                        label="Weapon zone", edgecolors="white", linewidths=0.5)
            ax2.set_xlabel("Range (m)", fontsize=12)
            ax2.set_ylabel("Doppler bin", fontsize=12)
            ax2.set_title(f"Doppler–Range — {len(pts)} pts", fontsize=12, fontweight="bold")
            ax2.grid(True, alpha=0.25)
            ax2.set_facecolor("#f0f2f5")
            ax2.axvspan(1.17, 1.95, color="red", alpha=0.06)
            ax2.set_xlim(0.5, 3.0)
            ax2.set_ylim(0, 16)

            writer.grab_frame()
            print(f"  frame {int(f)} written")

    print(f"saved: {args.output}")


if __name__ == "__main__":
    raise SystemExit(main())
