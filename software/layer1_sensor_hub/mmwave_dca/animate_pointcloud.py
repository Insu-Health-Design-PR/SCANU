#!/usr/bin/env python3
"""Animated 3D point cloud video — paper-style, frame by frame.

Usage::

    python -m layer1_sensor_hub.mmwave_dca.animate_pointcloud \\
        data/point_clouds/weapon_1m.csv \\
        -o data/point_clouds/animation.mp4
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter


def main():
    p = argparse.ArgumentParser(description="Animate radar point cloud frames")
    p.add_argument("csv", help="Point cloud CSV")
    p.add_argument("--output", "-o", default="pointcloud_animation.mp4")
    p.add_argument("--fps", type=int, default=8)
    p.add_argument("--max-points", type=int, default=200)
    args = p.parse_args()

    data = np.loadtxt(args.csv, delimiter=",", skiprows=1)
    if data.ndim != 2 or data.shape[1] < 5:
        print(f"error: expected 5+ columns, got shape {data.shape}")
        return 1

    frames_u = np.unique(data[:, 0]).astype(int)
    frames_u.sort()
    print(f"Loaded {len(data)} points across {len(frames_u)} frames")

    fig = plt.figure(figsize=(16, 7))
    fig.suptitle("Radar Point Cloud — mmWave DCA1000 + IWR6843", fontsize=14, y=0.98)

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
            snr = pts[:, 4]

            # --- Bird's-eye ---
            ax1 = fig.add_subplot(121)
            ax1.clear()
            ax1.scatter(rng, ang, c=snr, cmap="jet", alpha=0.7, s=18,
                        edgecolors="k", linewidths=0.3, vmin=data[:, 4].min(),
                        vmax=data[:, 4].max())
            ax1.set_xlabel("Range (m)", fontsize=12)
            ax1.set_ylabel("Angle (rad)", fontsize=12)
            ax1.set_title(f"Bird's-Eye View — frame {int(f)}", fontsize=12, fontweight="bold")
            ax1.grid(True, alpha=0.3)
            ax1.set_facecolor("#f8f9fa")
            ax1.set_xlim(1.0, 2.2)
            ax1.set_ylim(-0.8, 0.8)

            # --- 3D ---
            ax2 = fig.add_subplot(122, projection="3d")
            ax2.clear()
            ax2.scatter(rng, ang, dop, c=snr, cmap="jet", alpha=0.7, s=14,
                        edgecolors="k", linewidths=0.2, vmin=data[:, 4].min(),
                        vmax=data[:, 4].max())
            ax2.set_xlabel("Range (m)", fontsize=12, labelpad=8)
            ax2.set_ylabel("Angle (rad)", fontsize=12, labelpad=8)
            ax2.set_zlabel("Doppler bin", fontsize=12, labelpad=8)
            ax2.set_title(f"3D Point Cloud — {len(pts)} pts", fontsize=12, fontweight="bold")
            ax2.set_xlim(1.0, 2.2)
            ax2.set_ylim(-0.8, 0.8)
            ax2.set_zlim(0, 16)
            ax2.view_init(elev=25, azim=-60)

            writer.grab_frame()
            print(f"  frame {int(f)} written")

    print(f"saved: {args.output}")


if __name__ == "__main__":
    raise SystemExit(main())
