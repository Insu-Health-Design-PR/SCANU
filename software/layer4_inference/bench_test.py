from __future__ import annotations

import argparse
import sys
from pathlib import Path

import weapon_ai.infer_thermal_objects as infer_thermal_objects

# Classifier checkpoints (BCE p(gun) heads); each pairs with every firearm weight below.
CLASSIFIER_CHECKPOINTS = [
    "trained_models/gun_detection/gun_prob_best.pt",
    "trained_models/gun_detection/gun_prob_smoke_best.pt",
]

# Firearm YOLO weights; each run goes under trained_models/outputs/thermal_previews/<clf_dir>__<stem>/.
FIREARM_YOLO_WEIGHTS = [
    "trained_models/gun_detection/gun_thermal_colormap_best.pt",
]


def _preview_subdir(clf_checkpoint: Path, firearm_yolo: Path | None) -> str:
    """Folder name under thermal_previews so runs are grouped by model combo."""
    clf = clf_checkpoint.resolve()
    clf_tag = clf.parent.name if clf.parent.name else clf.stem
    if firearm_yolo is not None and firearm_yolo.is_file():
        gun_tag = firearm_yolo.resolve().stem
    else:
        gun_tag = "default_firearm_yolo"
    return f"{clf_tag}__{gun_tag}"


def _resolve_under_repo(repo_root: Path, p: str | Path) -> Path:
    path = Path(p).expanduser()
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    return path


def _use_gun_thermal_preset(video: Path) -> bool:
    """Thermal / pseudo-thermal streams need --gun_thermal; plain RGB clips use default firearm settings."""
    stem = video.stem.lower()
    if "_pseudo_thermal" in stem or "_thermal" in stem or stem.endswith("thermal"):
        return True
    if "_rgb" in stem or stem.endswith("rgb"):
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Bench infer_thermal_objects on dual_camera mp4s.")
    parser.add_argument(
        "--max-videos",
        type=int,
        default=0,
        help="If >0, only process the first N videos (sorted by name).",
    )
    parser.add_argument(
        "--video-pattern",
        type=str,
        default="*.mp4",
        help='Glob under dual_camera, e.g. "*_pseudo_thermal.mp4" or "*.mp4".',
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    source_dir = repo_root / "data" / "collecting_data" / "dual_camera"
    previews_root = repo_root / "trained_models" / "outputs" / "thermal_previews"

    videos = sorted(source_dir.glob(args.video_pattern))
    if args.max_videos > 0:
        videos = videos[: args.max_videos]
    if not videos:
        print(f"No files matched {source_dir} / {args.video_pattern}")
        return

    out_dirs: list[Path] = []
    for clf_rel in CLASSIFIER_CHECKPOINTS:
        clf_path = _resolve_under_repo(repo_root, clf_rel)
        if not clf_path.is_file():
            print(f"Skip missing classifier: {clf_path}")
            continue

        for gun_rel in FIREARM_YOLO_WEIGHTS:
            gun_yolo = _resolve_under_repo(repo_root, gun_rel)
            if not gun_yolo.is_file():
                print(f"Skip missing firearm weights: {gun_yolo}")
                continue

            sub = _preview_subdir(clf_path, gun_yolo)
            out_dir = previews_root / sub
            out_dir.mkdir(parents=True, exist_ok=True)
            if out_dir not in out_dirs:
                out_dirs.append(out_dir)

            print(
                f"\n{'=' * 60}\n"
                f"Classifier: {clf_path.parent.name}/{clf_path.name}\n"
                f"Firearm YOLO: {gun_yolo.name}  ->  {out_dir}\n"
                f"{'=' * 60}"
            )

            for video in videos:
                thermal_preset = _use_gun_thermal_preset(video)
                out_file = out_dir / f"{video.stem}_bench.mp4"
                argv = [
                    "infer_thermal_objects",
                    "--checkpoint",
                    str(clf_path),
                    "--source",
                    str(video),
                    "--output",
                    str(out_file),
                    "--yolo_classes",
                    "0",
                    "--no_imshow",
                    "--gun_yolo_model",
                    str(gun_yolo),
                ]
                if thermal_preset:
                    argv.append("--gun_thermal")
                argv.extend(["--gun_roi_pad_px", "8"])

                tag = "thermal_preset" if thermal_preset else "rgb_default"
                print(f"\n=== {clf_path.parent.name} | {gun_yolo.name} | {video.name} ({tag}) ===")
                old_argv = sys.argv
                try:
                    sys.argv = argv
                    infer_thermal_objects.main()
                finally:
                    sys.argv = old_argv

    if not out_dirs:
        print("No valid classifier/firearm pairs; nothing to run.")
        return

    print(f"\nDone. Outputs under {previews_root}:")
    for d in sorted(set(out_dirs), key=lambda p: str(p)):
        print(f"  - {d}")


if __name__ == "__main__":
    main()
