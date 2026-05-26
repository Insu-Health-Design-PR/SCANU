#!/usr/bin/env python3
"""Animated 3D point cloud — one frame at a time, saved as MP4.

Typical usage::

    python -m layer1_sensor_hub.mmwave_dca.animate_pointcloud \\
        data/point_clouds/weapon_1m.csv \\
        -o data/point_clouds/animation.mp4
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="Animate point cloud across frames")
    p.add_argument("csv", help="Point cloud CSV from mmwave_run_detection")
    p.add_argument("--output", "-o", default="pointcloud_animation.mp4")
    p.add_argument("--fps", type=int, default=5)
    p.add_argument("--max-points", type=int, default=200)
    args = p.parse_args()

    data = np.loadtxt(args.csv, delimiter=",", skiprows=1)
    if data.ndim != 2 or data.shape[1] < 5:
        print(f"error: expected 5+ columns, got shape {data.shape}")
        return 1

    frames = np.unique(data[:, 0]).astype(int)
    frames.sort()
    print(f"Loaded {len(data)} points across {len(frames)} frames")

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")

    writer = FFMpegWriter(fps=args.fps)
    n_frames = len(frames)
    n_show = min(n_frames, 100)

    with writer.saving(fig, args.output, dpi=150):
        for idx in range(0, n_frames, max(1, n_frames // n_show)):
            f = frames[idx]
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

            ax.clear()
            sc = ax.scatter(rng, ang, dop, c=snr, cmap="jet", alpha=0.7, s=15)
            ax.set_xlabel("Range (m)")
            ax.set_ylabel("Angle (rad)")
            ax.set_zlabel("Doppler bin")
            ax.set_title(f"Frame {int(f)} — {len(pts)} points")
            ax.set_xlim(1.0, 2.0)
            ax.set_ylim(-1.0, 1.0)
            ax.set_zlim(0, 16)
            fig.colorbar(sc, ax=ax, label="SNR (dB)", shrink=0.6)

            writer.grab_frame()
            print(f"  frame {int(f)} written")

    print(f"saved: {args.output}")


if __name__ == "__main__":
    raise SystemExit(main())
