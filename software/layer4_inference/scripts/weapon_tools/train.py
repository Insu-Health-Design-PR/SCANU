"""
Train a binary classifier (safe vs unsafe).

- video_mode composite (default): clips from manifest.jsonl (side-by-side / full frame).
- video_mode thermal: *_thermal.mp4 (and legacy *_panels/thermal.mp4) under collecting_data.
- video_mode uclm: data/datasets/uclm/UCLM/UCLM_Thermal_Imaging_Dataset Handgun/ vs No_Gun/ sequence folders with video.mp4.
- video_mode gun_prob: mixed CPD stills + UCLM frames, trained with BCE as P(gun).

Optional --init_checkpoint loads weights for fine-tuning (same --arch as the checkpoint).

Run from repo root:
  python -m scripts.weapon_tools.train --data_root data --epochs 40
  python -m scripts.weapon_tools.train --video_mode thermal --crop_mode full --output_dir trained_models/person_detection/thermal_run
  python -m scripts.weapon_tools.train --video_mode thermal --init_checkpoint trained_models/person_detection/best.pt --output_dir trained_models/person_detection/thermal_ft
  python -m scripts.weapon_tools.train --video_mode uclm --crop_mode full --output_dir trained_models/person_detection/uclm_run
  python -m scripts.weapon_tools.train --video_mode gun_prob --cpd_split data/datasets/gun/cpd_split --output_dir trained_models/gun_detection
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from torch.utils.data import ConcatDataset, DataLoader, WeightedRandomSampler
from tqdm import tqdm

from weapon_ai.modeling import build_gun_prob_model, build_model

from .dataset import CompositeVideoFrameDataset
from .gun_prob_dataset import CPDGunImageDataset, UCLMGunFrameDataset
from .manifest import ManifestRow, iter_existing_videos, load_manifest
from .thermal_clips import discover_thermal_training_rows
from .uclm_thermal import discover_uclm_rows


def _video_stratified_split(
    rows: list[ManifestRow], val_fraction: float, seed: int
) -> tuple[list[ManifestRow], list[ManifestRow]]:
    paths = [str(r.video) for r in rows]
    labels = [r.label_id for r in rows]
    train_p, val_p, train_y, val_y = train_test_split(
        paths,
        labels,
        test_size=val_fraction,
        stratify=labels,
        random_state=seed,
    )
    train_set = set(train_p)
    train_rows = [r for r in rows if str(r.video) in train_set]
    val_rows = [r for r in rows if str(r.video) not in train_set]
    return train_rows, val_rows


def _class_weights_from_labels(labels: list[int], device: torch.device) -> torch.Tensor:
    n0 = max(1, sum(1 for y in labels if y == 0))
    n1 = max(1, sum(1 for y in labels if y == 1))
    # inverse frequency, normalized
    w0 = (len(labels) / (2 * n0))
    w1 = (len(labels) / (2 * n1))
    return torch.tensor([w0, w1], dtype=torch.float32, device=device)


def _merge_labels(*datasets_with_labels) -> list[int]:
    labels: list[int] = []
    for ds in datasets_with_labels:
        if ds is None:
            continue
        labels.extend(int(x) for x in ds.labels)
    return labels


def _train_gun_prob(args) -> None:
    cpd_root = Path(args.cpd_split).resolve()
    cpd_train_dir = cpd_root / "train"
    cpd_val_dir = cpd_root / "val"

    uroot = args.uclm_root
    if uroot is None:
        uroot = args.data_root / "datasets" / "uclm" / "UCLM" / "UCLM_Thermal_Imaging_Dataset"
    uroot = Path(uroot).resolve()

    u_rows: list[ManifestRow] = []
    if uroot.is_dir():
        u_rows = discover_uclm_rows(uroot)

    u_train_rows: list[ManifestRow] = []
    u_val_rows: list[ManifestRow] = []
    if u_rows:
        u_train_rows, u_val_rows = _video_stratified_split(u_rows, args.val_fraction, args.seed)

    cpd_train_ds = (
        CPDGunImageDataset(cpd_train_dir, image_size=args.image_size, augment=True)
        if cpd_train_dir.is_dir()
        else None
    )
    cpd_val_ds = (
        CPDGunImageDataset(cpd_val_dir, image_size=args.image_size, augment=False)
        if cpd_val_dir.is_dir()
        else None
    )
    u_train_ds = (
        UCLMGunFrameDataset(
            u_train_rows,
            frames_per_video=args.frames_per_video,
            image_size=args.image_size,
            augment=True,
        )
        if u_train_rows
        else None
    )
    u_val_ds = (
        UCLMGunFrameDataset(
            u_val_rows,
            frames_per_video=args.frames_per_video,
            image_size=args.image_size,
            augment=False,
        )
        if u_val_rows
        else None
    )

    train_parts = [d for d in [cpd_train_ds, u_train_ds] if d is not None and len(d) > 0]
    val_parts = [d for d in [cpd_val_ds, u_val_ds] if d is not None and len(d) > 0]
    if not train_parts or not val_parts:
        print("gun_prob mode needs train+val data from CPD split and/or UCLM.")
        print(f"CPD checked at: {cpd_root}")
        print(f"UCLM checked at: {uroot}")
        return

    train_ds = train_parts[0] if len(train_parts) == 1 else ConcatDataset(train_parts)
    val_ds = val_parts[0] if len(val_parts) == 1 else ConcatDataset(val_parts)
    labels = _merge_labels(cpd_train_ds, u_train_ds)
    if not labels or len(set(labels)) < 2:
        print("gun_prob mode needs both no_gun(0) and gun(1) samples in training data.")
        return
    counts = np.bincount(labels, minlength=2)
    weights_each = 1.0 / np.maximum(counts[np.array(labels)], 1)
    sampler = WeightedRandomSampler(
        torch.from_numpy(weights_each).double(),
        num_samples=len(labels),
        replacement=True,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    print(
        f"gun_prob mode | train samples: {len(train_ds)} | val samples: {len(val_ds)} | "
        f"class counts (train): {counts.tolist()}"
    )
    print(
        f"Sources -> CPD train/val: {0 if cpd_train_ds is None else len(cpd_train_ds)}/"
        f"{0 if cpd_val_ds is None else len(cpd_val_ds)} | "
        f"UCLM train/val: {0 if u_train_ds is None else len(u_train_ds)}/"
        f"{0 if u_val_ds is None else len(u_val_ds)}"
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        sampler=sampler,
        num_workers=0,
        pin_memory=device.type == "cuda",
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=device.type == "cuda",
    )

    model = build_gun_prob_model(args.arch).to(device)
    if args.init_checkpoint is not None:
        ic = args.init_checkpoint
        if not ic.is_file():
            raise SystemExit(f"--init_checkpoint not found: {ic}")
        payload = torch.load(ic, map_location=device, weights_only=False)
        model.load_state_dict(payload["model"], strict=True)
        print(f"Loaded weights from {ic}")
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    n0 = max(1, int(counts[0]))
    n1 = max(1, int(counts[1]))
    pos_weight = torch.tensor([n0 / n1], dtype=torch.float32, device=device)
    crit = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    best_acc = 0.0
    best_path = args.output_dir / "best.pt"

    for epoch in range(1, args.epochs + 1):
        model.train()
        loss_tr = 0.0
        n_tr = 0
        for x, y in tqdm(train_loader, desc=f"epoch {epoch} train", leave=False):
            x = x.to(device, non_blocking=True)
            yf = y.to(device, non_blocking=True).float()
            opt.zero_grad(set_to_none=True)
            logits = model(x).reshape(-1)
            loss = crit(logits, yf)
            loss.backward()
            opt.step()
            loss_tr += loss.item() * x.size(0)
            n_tr += x.size(0)

        model.eval()
        correct = 0
        total = 0
        loss_va = 0.0
        with torch.no_grad():
            for x, y in val_loader:
                x = x.to(device, non_blocking=True)
                yf = y.to(device, non_blocking=True).float()
                logits = model(x).reshape(-1)
                loss_va += crit(logits, yf).item() * x.size(0)
                pred = (torch.sigmoid(logits) >= 0.5).long()
                correct += (pred == y.to(device)).sum().item()
                total += y.size(0)

        acc = correct / max(total, 1)
        print(
            f"epoch {epoch} | train loss {loss_tr / max(n_tr, 1):.4f} | "
            f"val loss {loss_va / max(total, 1):.4f} | val acc {acc:.4f}"
        )
        if acc >= best_acc:
            best_acc = acc
            torch.save(
                {
                    "model": model.state_dict(),
                    "arch": args.arch,
                    "video_mode": args.video_mode,
                    "objective": "gun_prob_bce",
                    "num_classes": 1,
                    "preprocess": "gray3ch_224_imagenet_norm",
                    "label_map": {"no_gun": 0, "gun": 1},
                },
                best_path,
            )

    meta = {
        "best_val_acc": best_acc,
        "checkpoint": str(best_path),
        "arch": args.arch,
        "video_mode": args.video_mode,
        "objective": "gun_prob_bce",
        "init_checkpoint": str(args.init_checkpoint) if args.init_checkpoint else None,
        "cpd_root": str(cpd_root),
        "uclm_root": str(uroot),
        "train_samples": len(train_ds),
        "val_samples": len(val_ds),
    }
    (args.output_dir / "train_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Saved {best_path} (best val acc {best_acc:.4f})")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data_root", type=Path, default=Path("data"))
    p.add_argument(
        "--video_mode",
        choices=["composite", "thermal", "uclm", "gun_prob"],
        default="composite",
        help="composite: manifest. thermal: *_thermal.mp4 under collecting_data. "
        "uclm: UCLM Handgun/No_Gun video.mp4. gun_prob: mixed CPD stills + UCLM frames with BCE.",
    )
    p.add_argument(
        "--uclm_root",
        type=Path,
        default=None,
        help="For video_mode=uclm: folder containing Handgun/ and No_Gun/. "
        "Default: data_root/datasets/uclm/UCLM/UCLM_Thermal_Imaging_Dataset",
    )
    p.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/collecting_data/manifest.jsonl"),
    )
    p.add_argument(
        "--init_checkpoint",
        type=Path,
        default=None,
        help="Optional .pt to load before training (fine-tune). Must match --arch.",
    )
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch_size", type=int, default=16)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--weight_decay", type=float, default=1e-4)
    p.add_argument("--frames_per_video", type=int, default=12)
    p.add_argument("--image_size", type=int, default=224)
    p.add_argument("--val_fraction", type=float, default=0.25)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--arch", type=str, default="mobilenet_v3_small")
    p.add_argument(
        "--crop_mode",
        type=str,
        default="full",
        choices=["full", "left_third", "center_third"],
        help="left_third ~ thermal if it is the left panel; adjust after inspecting a frame.",
    )
    p.add_argument(
        "--output_dir",
        type=Path,
        default=None,
        help="Where to write best.pt and train_meta.json. Default: trained_models/person_detection "
        "(composite/thermal/uclm) or trained_models/gun_detection (gun_prob).",
    )
    p.add_argument(
        "--cpd_split",
        type=Path,
        default=Path("data/datasets/gun/cpd_split"),
        help="For gun_prob mode: CPD root containing train/ and val/ with withgun/withoutgun.",
    )
    args = p.parse_args()
    if args.output_dir is None:
        args.output_dir = Path(
            "trained_models/gun_detection"
            if args.video_mode == "gun_prob"
            else "trained_models/person_detection"
        )

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if args.video_mode == "gun_prob":
        _train_gun_prob(args)
        return

    collecting = args.data_root / "collecting_data"
    if args.video_mode == "thermal":
        rows = discover_thermal_training_rows(collecting)
        missing = 0
        if not rows:
            print(
                f"No thermal training files under {collecting}. "
                "Expected names like clip_thermal.mp4 or clip_panels/thermal.mp4"
            )
            return
        print(f"Thermal mode: {len(rows)} clip(s) (*_thermal.mp4 / *_panels/thermal.mp4)")
    elif args.video_mode == "uclm":
        uroot = args.uclm_root
        if uroot is None:
            uroot = args.data_root / "datasets" / "uclm" / "UCLM" / "UCLM_Thermal_Imaging_Dataset"
        uroot = Path(uroot).resolve()
        missing = 0
        if not uroot.is_dir():
            print(f"UCLM root not found: {uroot}")
            return
        rows = discover_uclm_rows(uroot)
        if not rows:
            print(f"No video.mp4 under Handgun/ or No_Gun/ in {uroot}")
            return
        print(f"UCLM mode: {len(rows)} sequence(s) from {uroot}")
        if args.crop_mode != "full":
            print("Note: UCLM clips are single-panel thermal; use --crop_mode full (default ok).")
    else:
        manifest_path = args.manifest
        if not manifest_path.is_file():
            manifest_path = collecting / "manifest.jsonl"

        all_rows = load_manifest(manifest_path, args.data_root)
        rows = list(iter_existing_videos(all_rows))
        missing = len(all_rows) - len(rows)
        if missing:
            print(f"Warning: {missing} manifest entries have no video file under {args.data_root}")
    if len(rows) < 4:
        print(
            "Need at least a few video files. Place .mp4 files next to the JSON under "
            "data/collecting_data/safe/... and data/collecting_data/unsafe/..., "
            "or extract data.zip here."
        )
        return

    if len(set(r.label_id for r in rows)) < 2:
        print("Need both safe and unsafe videos with files present to train.")
        return

    train_rows, val_rows = _video_stratified_split(rows, args.val_fraction, args.seed)
    if not val_rows:
        print("Validation split empty; add more videos or lower --val_fraction.")
        return

    train_ds = CompositeVideoFrameDataset(
        train_rows,
        frames_per_video=args.frames_per_video,
        image_size=args.image_size,
        augment=True,
        crop_mode=args.crop_mode,
    )
    val_ds = CompositeVideoFrameDataset(
        val_rows,
        frames_per_video=args.frames_per_video,
        image_size=args.image_size,
        augment=False,
        crop_mode=args.crop_mode,
    )
    if len(train_ds) == 0:
        print("Training dataset empty (could not read frames from videos).")
        return

    labels = [train_ds.samples[i][2] for i in range(len(train_ds))]
    counts = np.bincount(labels, minlength=2)
    weights_each = 1.0 / np.maximum(counts[labels], 1)
    sampler = WeightedRandomSampler(
        torch.from_numpy(weights_each).double(),
        num_samples=len(train_ds),
        replacement=True,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device} | train videos: {len(train_rows)} | val videos: {len(val_rows)}")
    print(f"Train frames: {len(train_ds)} | Val frames: {len(val_ds)} | class counts (train): {counts.tolist()}")

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        sampler=sampler,
        num_workers=0,
        pin_memory=device.type == "cuda",
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=device.type == "cuda",
    )

    model = build_model(args.arch, num_classes=2).to(device)
    if args.init_checkpoint is not None:
        ic = args.init_checkpoint
        if not ic.is_file():
            raise SystemExit(f"--init_checkpoint not found: {ic}")
        payload = torch.load(ic, map_location=device, weights_only=False)
        model.load_state_dict(payload["model"], strict=True)
        print(f"Loaded weights from {ic}")
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    ce_weights = _class_weights_from_labels(list(labels), device)
    crit = nn.CrossEntropyLoss(weight=ce_weights)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    best_acc = 0.0
    best_path = args.output_dir / "best.pt"

    for epoch in range(1, args.epochs + 1):
        model.train()
        loss_tr = 0.0
        n_tr = 0
        for x, y in tqdm(train_loader, desc=f"epoch {epoch} train", leave=False):
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            logits = model(x)
            loss = crit(logits, y)
            loss.backward()
            opt.step()
            loss_tr += loss.item() * x.size(0)
            n_tr += x.size(0)

        model.eval()
        correct = 0
        total = 0
        loss_va = 0.0
        with torch.no_grad():
            for x, y in val_loader:
                x = x.to(device, non_blocking=True)
                y = y.to(device, non_blocking=True)
                logits = model(x)
                loss_va += crit(logits, y).item() * x.size(0)
                pred = logits.argmax(dim=1)
                correct += (pred == y).sum().item()
                total += y.size(0)

        acc = correct / max(total, 1)
        print(
            f"epoch {epoch} | train loss {loss_tr / max(n_tr, 1):.4f} | "
            f"val loss {loss_va / max(total, 1):.4f} | val acc {acc:.4f}"
        )
        if acc >= best_acc:
            best_acc = acc
            torch.save(
                {
                    "model": model.state_dict(),
                    "arch": args.arch,
                    "crop_mode": args.crop_mode,
                    "video_mode": args.video_mode,
                    "label_map": {"safe": 0, "unsafe": 1},
                },
                best_path,
            )

    meta = {
        "best_val_acc": best_acc,
        "checkpoint": str(best_path),
        "arch": args.arch,
        "crop_mode": args.crop_mode,
        "video_mode": args.video_mode,
        "init_checkpoint": str(args.init_checkpoint) if args.init_checkpoint else None,
        "train_videos": len(train_rows),
        "val_videos": len(val_rows),
    }
    (args.output_dir / "train_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Saved {best_path} (best val acc {best_acc:.4f})")


if __name__ == "__main__":
    main()
