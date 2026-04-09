#!/usr/bin/env python3
"""
Build a **safe / unsafe** image dataset from ``~/Desktop/collecting_data`` MP4s and train
a CNN, or print a **YOLO classify** command.

From ``software/``::

  # 1) Export JPEGs — every frame: add --all-frames (big disk); else subsample with --frames-per-video
  python3 -m layer4_inference.examples.train_collecting_data_classifier build \\
    --data-root ~/Desktop/collecting_data --out ~/Desktop/l4_safe_unsafe_jpg --all-frames

  # 2) Train PyTorch ResNet-18 classifier (needs torchvision)
  python3 -m layer4_inference.examples.train_collecting_data_classifier train-cnn \\
    --dataset ~/Desktop/l4_safe_unsafe_jpg --epochs 30 --out ~/Desktop/l4_safe_unsafe_jpg/best.pt

  # 3) Re-score val or test with a saved checkpoint
  python3 -m layer4_inference.examples.train_collecting_data_classifier eval \\
    --weights ~/Desktop/l4_safe_unsafe_jpg/best.pt --dataset ~/Desktop/l4_safe_unsafe_jpg --split test

  # 4) YOLO classify (install ultralytics separately)
  python3 -m layer4_inference.examples.train_collecting_data_classifier yolo-hint \\
    --dataset ~/Desktop/l4_safe_unsafe_jpg
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_software = Path(__file__).resolve().parents[2]
if str(_software) not in sys.path:
    sys.path.insert(0, str(_software))

from layer4_inference.collecting_data_vision import (  # noqa: E402
    build_classify_image_dataset,
    list_labeled_mp4s,
    yolo_classify_train_hint,
)

# Lazy-import safe_unsafe_cnn (torch) only for train-cnn / eval so ``build``/``list`` work
# even when NumPy/torch are temporarily broken (e.g. ultralytics upgraded numpy to 2.x).


def _cmd_list(args: argparse.Namespace) -> int:
    root = Path(args.data_root).expanduser().resolve()
    vids = list_labeled_mp4s(root)
    print(f"root={root}  mp4_count={len(vids)}")
    for v in vids[: args.limit] if args.limit > 0 else vids:
        print(f"  [{v.split_name}] {v.scenario}  {v.path.name}")
    if args.limit > 0 and len(vids) > args.limit:
        print(f"  ... ({len(vids) - args.limit} more)")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    summary = build_classify_image_dataset(
        args.data_root,
        args.out,
        frames_per_video=int(args.frames_per_video),
        all_frames=bool(args.all_frames),
        val_fraction=float(args.val_fraction),
        test_fraction=float(args.test_fraction),
        seed=int(args.seed),
        jpeg_quality=int(args.jpeg_quality),
        overwrite=bool(args.overwrite),
    )
    for k, v in summary.items():
        print(f"{k}: {v}")
    print()
    print(yolo_classify_train_hint(summary["yaml_path"]))
    return 0


def _cmd_train_cnn(args: argparse.Namespace) -> int:
    from layer4_inference.safe_unsafe_cnn import train_classifier

    train_classifier(
        args.dataset,
        epochs=int(args.epochs),
        batch_size=int(args.batch_size),
        lr=float(args.lr),
        img_size=int(args.img_size),
        num_workers=int(args.workers),
        pretrained_backbone=bool(args.pretrained),
        device=args.device or None,
        out_weights=args.out,
    )
    return 0


def _cmd_eval(args: argparse.Namespace) -> int:
    from layer4_inference.safe_unsafe_cnn import evaluate_classifier

    evaluate_classifier(
        args.weights,
        args.dataset,
        split=args.split,
        batch_size=int(args.batch_size),
        img_size=int(args.img_size) if args.img_size > 0 else None,
        num_workers=int(args.workers),
        device=args.device or None,
        verbose=True,
    )
    return 0


def _cmd_yolo_hint(args: argparse.Namespace) -> int:
    root = Path(args.dataset).expanduser().resolve()
    y = root / "data.yaml"
    if not y.is_file():
        print(f"Missing {y} — run `build` first.", file=sys.stderr)
        return 2
    print(yolo_classify_train_hint(y))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Layer 4: safe/unsafe vision dataset + CNN training")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List labeled MP4s under data root")
    p_list.add_argument("--data-root", type=Path, default=Path.home() / "Desktop" / "collecting_data")
    p_list.add_argument("--limit", type=int, default=0, help="Max lines (0 = all)")
    p_list.set_defaults(func=_cmd_list)

    p_build = sub.add_parser("build", help="Export train/val JPEGs + data.yaml")
    p_build.add_argument("--data-root", type=Path, default=Path.home() / "Desktop" / "collecting_data")
    p_build.add_argument(
        "--out",
        type=Path,
        default=Path.home() / "Desktop" / "l4_safe_unsafe_jpg",
        help="Output directory for train/val/safe/unsafe + data.yaml",
    )
    p_build.add_argument("--frames-per-video", type=int, default=8)
    p_build.add_argument(
        "--all-frames",
        action="store_true",
        help="Export every decodable frame per MP4 (ignores --frames-per-video; large disk use).",
    )
    p_build.add_argument("--val-fraction", type=float, default=0.2)
    p_build.add_argument(
        "--test-fraction",
        type=float,
        default=0.0,
        help="Fraction of videos per class for held-out test (0 = train+val only). Recommended ~0.1–0.2.",
    )
    p_build.add_argument("--seed", type=int, default=42)
    p_build.add_argument("--jpeg-quality", type=int, default=92)
    p_build.add_argument("--overwrite", action="store_true", help="Clear existing JPGs in class dirs")
    p_build.set_defaults(func=_cmd_build)

    p_train = sub.add_parser("train-cnn", help="Train ResNet-18 on exported dataset")
    p_train.add_argument("--dataset", type=Path, required=True, help="Directory with train/ and val/")
    p_train.add_argument("--epochs", type=int, default=30)
    p_train.add_argument("--batch-size", type=int, default=16)
    p_train.add_argument("--lr", type=float, default=1e-3)
    p_train.add_argument("--img-size", type=int, default=224)
    p_train.add_argument("--workers", type=int, default=2)
    p_train.add_argument("--pretrained", action="store_true", help="ImageNet weights for backbone")
    p_train.add_argument("--device", type=str, default="", help="cuda / cpu / mps (empty = auto)")
    p_train.add_argument("--out", type=Path, default=None, help="Weights .pt path")
    p_train.set_defaults(func=_cmd_train_cnn)

    p_ev = sub.add_parser("eval", help="Confusion matrix + accuracy on val or test split")
    p_ev.add_argument("--weights", type=Path, required=True, help="safe_unsafe_cnn.pt")
    p_ev.add_argument("--dataset", type=Path, required=True, help="Dataset root with train/val/test/")
    p_ev.add_argument("--split", type=str, default="test", choices=("train", "val", "test"))
    p_ev.add_argument("--batch-size", type=int, default=16)
    p_ev.add_argument("--img-size", type=int, default=0, help="0 = use value from checkpoint")
    p_ev.add_argument("--workers", type=int, default=2)
    p_ev.add_argument("--device", type=str, default="", help="cuda / cpu (empty = auto)")
    p_ev.set_defaults(func=_cmd_eval)

    p_yolo = sub.add_parser("yolo-hint", help="Print yolo classify train command")
    p_yolo.add_argument("--dataset", type=Path, required=True)
    p_yolo.set_defaults(func=_cmd_yolo_hint)

    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
