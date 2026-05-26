"""Run raw ADC weapon detection on a captured adc_data.bin file.

Outputs are saved to ``data/`` inside the module directory
(``layer1_sensor_hub/mmwave_dca/data/``).

Usage::

    python -m layer1_sensor_hub.mmwave_dca.mmwave_run_detection \\
        --input captures/test_10s.bin \\
        --chirps 16 --rx 4 --samples 384 \\
        --allow-truncate \\
        --output-csv data/detection_results.csv \\
        --output-plot data/weapon_score_timeline.png

Point cloud outputs::

    --output-point-cloud-csv data/point_clouds/my_capture.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .adc_reader import AdcCaptureShape, read_adc_data
from .mmwave_raw_adc_detector import RawAdcWeaponDetector, WeaponZoneParams


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect concealed weapons in raw DCA1000 ADC captures"
    )
    parser.add_argument("--input", required=True, help="Path to adc_data.bin")
    parser.add_argument("--chirps", type=int, default=16)
    parser.add_argument("--rx", type=int, default=4)
    parser.add_argument("--samples", type=int, default=384)
    parser.add_argument("--iq-order", choices=("ti", "iq"), default="ti")
    parser.add_argument("--allow-truncate", action="store_true")
    parser.add_argument("--max-frames", type=int, default=0, help="Limit frames to process (0 = all)")
    parser.add_argument("--output-csv", default="", help="Save per-frame results to CSV")
    parser.add_argument("--output-plot", default="", help="Save weapon score timeline plot")
    parser.add_argument("--output-point-cloud", default="", help="Save point cloud 3D scatter plot")
    parser.add_argument("--output-point-cloud-csv", default="",
                        help="Save point cloud coordinates as CSV (frame,range_bin,doppler_bin,angle_rad,snr)")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"error: input not found: {args.input}")
        return 1

    nbytes = input_path.stat().st_size
    chirps, rx, samples = args.chirps, args.rx, args.samples
    frames_in_file = nbytes // (4 * chirps * rx * samples)
    shape = AdcCaptureShape(
        frames=frames_in_file,
        chirps=chirps,
        rx=rx,
        samples=samples,
    )

    print(f"Loading: {input_path} ({nbytes} bytes, ~{frames_in_file} frames)")
    adc = read_adc_data(
        input_path,
        shape,
        iq_order=args.iq_order,
        allow_truncate=args.allow_truncate,
    )
    total_frames = adc.shape[0]
    max_frames = args.max_frames if args.max_frames > 0 else total_frames
    max_frames = min(max_frames, total_frames)
    print(f"Processing: {max_frames} / {total_frames} frames")

    detector = RawAdcWeaponDetector()

    scores = []
    all_features = []
    total_points = 0
    save_pc = bool(args.output_point_cloud_csv)
    all_point_clouds = [] if save_pc else None

    for i in range(max_frames):
        result = detector.detect(adc[i], frame_number=i)
        scores.append(result.weapon_score)
        all_features.append(result.features)
        n_pts = len(result.point_cloud) if result.point_cloud is not None else 0
        total_points += n_pts
        if save_pc and result.point_cloud is not None and len(result.point_cloud) > 0:
            pc = result.point_cloud.copy()
            frame_col = np.full((pc.shape[0], 1), i, dtype=np.float32)
            all_point_clouds.append(np.concatenate([frame_col, pc], axis=1))
        if (i + 1) % 50 == 0 or i == 0 or i == max_frames - 1:
            print(
                f"  frame {i:4d}/{max_frames}  score={result.weapon_score:.4f}  "
                f"detections={result.features['n_cfar_detections']:4d}  "
                f"cloud_pts={n_pts:3d}"
            )

    scores_arr = np.array(scores)
    print(f"\nSummary:")
    print(f"  Frames processed: {max_frames}")
    print(f"  Weapon score   min={scores_arr.min():.4f}  max={scores_arr.max():.4f}  "
          f"mean={scores_arr.mean():.4f}  std={scores_arr.std():.4f}")
    print(f"  Total point cloud points: {total_points}")

    n_alarm = int(np.sum(scores_arr >= 0.65))
    print(f"  Frames above 0.65 threshold: {n_alarm} / {max_frames} "
          f"({100 * n_alarm / max_frames:.1f}%)")

    if args.output_csv:
        out_csv = Path(args.output_csv)
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        feature_keys = list(all_features[0].keys())
        with open(out_csv, "w") as f:
            f.write("frame,weapon_score," + ",".join(feature_keys) + "\n")
            for i, feat in enumerate(all_features):
                f.write(f"{i},{scores[i]:.6f}")
                for k in feature_keys:
                    f.write(f",{feat[k]}")
                f.write("\n")
        print(f"  CSV saved: {out_csv}")

    if args.output_plot:
        out_plot = Path(args.output_plot)
        out_plot.parent.mkdir(parents=True, exist_ok=True)
        try:
            import matplotlib.pyplot as plt

            plt.figure(figsize=(12, 4))
            plt.plot(scores, "b-", linewidth=0.8, label="Weapon score")
            plt.axhline(0.65, color="r", linestyle="--", alpha=0.6, label="Threshold (0.65)")
            plt.ylim(-0.05, 1.05)
            plt.xlabel("Frame")
            plt.ylabel("Weapon score")
            plt.title(f"Weapon Score Timeline — {input_path.name}")
            plt.legend()
            plt.tight_layout()
            plt.savefig(out_plot, dpi=150)
            plt.close()
            print(f"  Plot saved: {out_plot}")
        except ImportError:
            print("  warning: matplotlib not installed, skipping plot")

    if args.output_point_cloud:
        out_pc = Path(args.output_point_cloud)
        out_pc.parent.mkdir(parents=True, exist_ok=True)
        try:
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import Axes3D

            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection="3d")

            re_run = RawAdcWeaponDetector(zone=WeaponZoneParams(static_start=90, static_end=150))
            frame_clouds = []
            frame_skip = max(1, max_frames // 30)
            for i in range(0, max_frames, frame_skip):
                result = re_run.detect(adc[i], frame_number=i)
                if result.point_cloud is not None and len(result.point_cloud) > 0:
                    pc = result.point_cloud
                    range_m = pc[:, 0] * 0.013
                    doppler = pc[:, 1]
                    angle = pc[:, 2]
                    snr = pc[:, 3]
                    sc = ax.scatter(
                        range_m, angle, doppler,
                        c=snr, cmap="jet", alpha=0.6, s=8,
                    )
                    frame_clouds.append(i)

            ax.set_xlabel("Range (m)")
            ax.set_ylabel("Angle (rad)")
            ax.set_zlabel("Doppler bin")
            ax.set_title(f"Point Cloud — {input_path.name} ({len(frame_clouds)} frames)")
            plt.colorbar(sc, label="SNR (dB)")
            plt.tight_layout()
            plt.savefig(out_pc, dpi=150)
            plt.close()
            print(f"  Point cloud saved: {out_pc}")
        except ImportError:
            print("  warning: mpl_toolkits not installed, skipping point cloud")

    if args.output_point_cloud_csv and all_point_clouds:
        out_pc_csv = Path(args.output_point_cloud_csv)
        out_pc_csv.parent.mkdir(parents=True, exist_ok=True)
        all_pc = np.concatenate(all_point_clouds, axis=0)
        np.savetxt(out_pc_csv, all_pc, delimiter=",",
                   header="frame,range_bin,doppler_bin,angle_rad,snr",
                   comments="", fmt="%.6f")
        print(f"  Point cloud CSV saved: {out_pc_csv} ({len(all_pc)} points)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
