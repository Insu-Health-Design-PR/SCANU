#!/usr/bin/env python3
"""Plot point cloud CSV in 3D (range, doppler, angle) colored by SNR."""

import argparse
import numpy as np
import matplotlib.pyplot as plt

def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv", help="Path to point cloud CSV from mmwave_run_detection.py")
    p.add_argument("--max-points", type=int, default=5000, help="Max points to plot")
    p.add_argument("--output", "-o", default="", help="Save to file instead of showing")
    args = p.parse_args()

    data = np.loadtxt(args.csv, delimiter=",", skiprows=1)
    if data.ndim != 2 or data.shape[1] < 5:
        print(f"error: expected 5+ columns, got shape {data.shape}")
        return 1

    frame = data[:, 0]
    rng   = data[:, 1] * 0.013
    dop   = data[:, 2]
    ang   = data[:, 3]
    snr   = data[:, 4]

    n = min(len(data), args.max_points)
    idx = np.random.choice(len(data), n, replace=False) if n < len(data) else slice(None)

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    sc = ax.scatter(rng[idx], ang[idx], dop[idx], c=snr[idx], cmap="jet",
                    alpha=0.6, s=12)
    ax.set_xlabel("Range (m)")
    ax.set_ylabel("Angle (rad)")
    ax.set_zlabel("Doppler bin")
    ax.set_title(f"Point Cloud ({n} points)")
    plt.colorbar(sc, label="SNR (dB)")

    if args.output:
        plt.savefig(args.output, dpi=150)
        print(f"saved: {args.output}")
    else:
        plt.show()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
