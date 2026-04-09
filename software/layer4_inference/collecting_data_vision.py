"""
Index ``*.mp4`` under a collecting-data tree and export frame JPEGs for **safe vs unsafe**
image classification (CNN, YOLO ``classify``, etc.).

Layout (input)::

    <root>/safe/<scenario>/*.mp4
    <root>/unsafe/<scenario>/*.mp4

Export layout (output)::

    <out>/train/safe/*.jpg
    <out>/train/unsafe/*.jpg
    <out>/val/safe/*.jpg
    <out>/val/unsafe/*.jpg
    <out>/test/safe/*.jpg   # optional held-out split (--test-fraction)
    <out>/test/unsafe/*.jpg
    <out>/data.yaml   # Ultralytics YOLO classify style
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

SplitName = Literal["safe", "unsafe"]


@dataclass(frozen=True, slots=True)
class LabeledVideo:
    """One MP4 with binary label from folder split."""

    path: Path
    """Absolute or resolved path to ``.mp4``."""

    label: int
    """0 = safe, 1 = unsafe."""

    split_name: SplitName
    """``safe`` or ``unsafe`` (folder name)."""

    scenario: str
    """Leaf scenario directory name."""


def iter_labeled_mp4s(root: Path | str) -> Iterator[LabeledVideo]:
    root_p = Path(root).expanduser().resolve()
    for split_name in ("safe", "unsafe"):
        label = 0 if split_name == "safe" else 1
        split_dir = root_p / split_name
        if not split_dir.is_dir():
            continue
        for scenario_dir in sorted(p for p in split_dir.iterdir() if p.is_dir()):
            scenario = scenario_dir.name
            for mp4 in sorted(scenario_dir.glob("*.mp4")):
                if mp4.is_file():
                    yield LabeledVideo(
                        path=mp4.resolve(),
                        label=label,
                        split_name=split_name,  # type: ignore[arg-type]
                        scenario=scenario,
                    )


def list_labeled_mp4s(root: Path | str) -> list[LabeledVideo]:
    return list(iter_labeled_mp4s(root))


def _split_label_list(
    items: list[LabeledVideo],
    *,
    val_fraction: float,
    test_fraction: float,
    rng: random.Random,
) -> tuple[list[LabeledVideo], list[LabeledVideo], list[LabeledVideo]]:
    """
    Per-class split: reserve ``test_fraction`` of videos for test, then ``val_fraction``
    of the **remainder** for validation. Stratify by repeating for each label.
    """
    items = items[:]
    rng.shuffle(items)
    n = len(items)
    n_test = int(round(n * float(test_fraction)))
    n_test = max(0, min(n_test, n))
    rest = n - n_test
    n_val = int(round(rest * float(val_fraction)))
    n_val = max(0, min(n_val, rest))
    test = items[:n_test]
    val = items[n_test : n_test + n_val]
    train = items[n_test + n_val :]
    return train, val, test


def _train_val_test_split(
    videos: list[LabeledVideo],
    *,
    val_fraction: float,
    test_fraction: float,
    seed: int,
) -> tuple[list[LabeledVideo], list[LabeledVideo], list[LabeledVideo]]:
    rng = random.Random(seed)
    by_label: dict[int, list[LabeledVideo]] = {0: [], 1: []}
    for v in videos:
        by_label[v.label].append(v)
    train: list[LabeledVideo] = []
    val: list[LabeledVideo] = []
    test: list[LabeledVideo] = []
    for label in (0, 1):
        tr, va, te = _split_label_list(
            by_label[label], val_fraction=val_fraction, test_fraction=test_fraction, rng=rng
        )
        train.extend(tr)
        val.extend(va)
        test.extend(te)
    return train, val, test


def scenario_counts(videos: list[LabeledVideo]) -> dict[str, int]:
    """Count videos per scenario name (handy to check train/val/test coverage)."""
    return dict(Counter(v.scenario for v in videos))


def _sample_frame_indices(num_frames: int, k: int) -> list[int]:
    if num_frames <= 0 or k <= 0:
        return []
    k = min(k, num_frames)
    if k == 1:
        return [num_frames // 2]
    return [int(round(i * (num_frames - 1) / (k - 1))) for i in range(k)]


def _class_dir_name(label: int) -> SplitName:
    return "safe" if label == 0 else "unsafe"


def build_classify_image_dataset(
    data_root: Path | str,
    output_dir: Path | str,
    *,
    frames_per_video: int = 8,
    all_frames: bool = False,
    val_fraction: float = 0.2,
    test_fraction: float = 0.0,
    seed: int = 42,
    jpeg_quality: int = 92,
    overwrite: bool = False,
) -> dict[str, object]:
    """
    Export frames from each MP4 into class folders for train/val/(test).

    If ``all_frames`` is True, writes **every** decodable frame (sequential read; ignores
    ``frames_per_video``). This can use a lot of disk; prefer subsampling for quick trials.

    Otherwise, samples up to ``frames_per_video`` evenly spaced indices.

    Splits are **by whole videos** (stratified by safe/unsafe), not by frame — so the same
    clip does not leak across splits. Use ``test_fraction > 0`` for a **held-out** set you
    never tune on; **do not train on that split** if you want an honest generalization estimate.

    Composite frames (Infineon + mmWave + thermal in one view) are unchanged: every exported
    JPEG is still the full frame; use identical resize/preprocessing at inference.

    Returns a small summary dict including paths to ``data.yaml`` and scenario histograms.
    """
    import cv2

    root_p = Path(data_root).expanduser().resolve()
    out_p = Path(output_dir).expanduser().resolve()
    videos = list_labeled_mp4s(root_p)
    if not videos:
        raise FileNotFoundError(f"No .mp4 files under {root_p} (expected safe/*/ and unsafe/*/)")

    train_v, val_v, test_v = _train_val_test_split(
        videos, val_fraction=val_fraction, test_fraction=test_fraction, seed=seed
    )

    splits = ("train", "val", "test") if test_fraction > 0 else ("train", "val")
    for sub in splits:
        for cls in ("safe", "unsafe"):
            d = out_p / sub / cls
            if overwrite and d.is_dir():
                for p in d.glob("*.jpg"):
                    p.unlink(missing_ok=True)
            d.mkdir(parents=True, exist_ok=True)

    def _export_split(split_name: str, vlist: list[LabeledVideo]) -> tuple[int, int]:
        n_img = 0
        n_skip = 0
        for v in vlist:
            cap = cv2.VideoCapture(str(v.path))
            if not cap.isOpened():
                n_skip += 1
                continue
            try:
                cls_name = _class_dir_name(v.label)
                stem = v.path.stem

                def _write_one(fi: int, frame) -> None:
                    nonlocal n_img
                    if frame.ndim == 2:
                        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                    out_name = f"{stem}__{v.scenario}__f{fi:06d}.jpg"
                    out_path = out_p / split_name / cls_name / out_name
                    cv2.imwrite(
                        str(out_path),
                        frame,
                        [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)],
                    )
                    n_img += 1

                if all_frames:
                    fi = 0
                    while True:
                        ok, frame = cap.read()
                        if not ok or frame is None:
                            break
                        _write_one(fi, frame)
                        fi += 1
                    if fi == 0:
                        n_skip += 1
                else:
                    n_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    indices = _sample_frame_indices(n_total, frames_per_video)
                    if not indices:
                        n_skip += 1
                        continue
                    for fi in indices:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
                        ok, frame = cap.read()
                        if not ok or frame is None:
                            continue
                        _write_one(fi, frame)
            finally:
                cap.release()
        return n_img, n_skip

    train_imgs, train_skip = _export_split("train", train_v)
    val_imgs, val_skip = _export_split("val", val_v)
    test_imgs = 0
    test_skip = 0
    if test_fraction > 0:
        test_imgs, test_skip = _export_split("test", test_v)

    yaml_path = out_p / "data.yaml"
    # Ultralytics classify: path + train/val relative dirs; names optional
    yaml_lines = [
        f"path: {out_p}",
        "train: train",
        "val: val",
    ]
    if test_fraction > 0:
        yaml_lines.append("test: test")
    yaml_lines.extend(
        [
            "nc: 2",
            "names:",
            "  0: safe",
            "  1: unsafe",
            "",
        ]
    )
    yaml_path.write_text("\n".join(yaml_lines), encoding="utf-8")

    out: dict[str, object] = {
        "data_root": root_p,
        "output_dir": out_p,
        "yaml_path": yaml_path,
        "videos_total": len(videos),
        "train_videos": len(train_v),
        "val_videos": len(val_v),
        "train_images": train_imgs,
        "val_images": val_imgs,
        "videos_skipped": train_skip + val_skip + test_skip,
        "all_frames": all_frames,
        "frames_per_video": frames_per_video,
        "val_fraction": val_fraction,
        "test_fraction": test_fraction,
        "train_scenarios": scenario_counts(train_v),
        "val_scenarios": scenario_counts(val_v),
    }
    if test_fraction > 0:
        out["test_videos"] = len(test_v)
        out["test_images"] = test_imgs
        out["test_scenarios"] = scenario_counts(test_v)
    return out


def yolo_classify_train_hint(yaml_path: Path | str) -> str:
    """Suggested command after ``pip install ultralytics``."""
    y = Path(yaml_path).expanduser().resolve()
    return (
        "YOLO classify (Ultralytics), after: pip install ultralytics\n"
        f"  yolo classify train data={y} model=yolov8n-cls.pt epochs=50 imgsz=224 batch=16"
    )
