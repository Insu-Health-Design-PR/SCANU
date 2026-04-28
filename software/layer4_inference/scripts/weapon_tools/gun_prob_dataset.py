from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset
from torchvision import datasets, transforms

from .manifest import ManifestRow


def _frame_count(cap: cv2.VideoCapture) -> int:
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if n > 0:
        return n
    cur = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    count = 0
    while True:
        ok, _ = cap.read()
        if not ok:
            break
        count += 1
    cap.set(cv2.CAP_PROP_POS_FRAMES, cur)
    return max(count, 1)


def build_gray3_tf(image_size: int, augment: bool) -> transforms.Compose:
    t_list: list[transforms.Compose | transforms.ToPILImage | transforms.Resize] = [
        transforms.ToPILImage(),
        transforms.Resize((image_size, image_size)),
    ]
    if augment:
        t_list.extend(
            [
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.ColorJitter(0.15, 0.15, 0.1, 0.05),
            ]
        )
    t_list.append(transforms.ToTensor())
    t_list.append(
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    )
    return transforms.Compose(t_list)


class CPDGunImageDataset(Dataset):
    """CPD stills from ImageFolder split, mapped to target 1=withgun, 0=withoutgun."""

    def __init__(self, split_dir: Path, image_size: int = 224, augment: bool = False) -> None:
        self.split_dir = split_dir.resolve()
        self.tf = build_gray3_tf(image_size, augment)
        self.ds = datasets.ImageFolder(self.split_dir)
        classes = set(self.ds.classes)
        if classes != {"withgun", "withoutgun"}:
            raise ValueError(
                f"Expected classes {{withgun, withoutgun}} under {self.split_dir}, got {self.ds.classes}"
            )
        self.gun_idx = self.ds.class_to_idx["withgun"]
        self.labels: list[int] = [
            1 if class_idx == self.gun_idx else 0 for _, class_idx in self.ds.samples
        ]

    def __len__(self) -> int:
        return len(self.ds.samples)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        path, class_idx = self.ds.samples[i]
        bgr = cv2.imread(path, cv2.IMREAD_COLOR)
        if bgr is None:
            bgr = np.zeros((224, 224, 3), dtype=np.uint8)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        x = self.tf(gray3)
        y = 1 if class_idx == self.gun_idx else 0
        return x, y


class UCLMGunFrameDataset(Dataset):
    """Sample frames from UCLM rows; target 1=gun (unsafe), 0=no_gun (safe)."""

    def __init__(
        self,
        rows: list[ManifestRow],
        frames_per_video: int,
        image_size: int = 224,
        augment: bool = False,
    ) -> None:
        self.samples: list[tuple[Path, int, int]] = []
        for r in rows:
            cap = cv2.VideoCapture(str(r.video))
            if not cap.isOpened():
                continue
            n = _frame_count(cap)
            cap.release()
            if n <= 0:
                continue
            idxs = np.linspace(0, n - 1, num=min(frames_per_video, n), dtype=int)
            for fi in idxs:
                self.samples.append((r.video, int(fi), int(r.label_id)))
        self.labels: list[int] = [int(lbl) for _, _, lbl in self.samples]
        self.tf = build_gray3_tf(image_size, augment)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        path, frame_idx, label = self.samples[i]
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            black = np.zeros((224, 224, 3), dtype=np.uint8)
            return self.tf(black), label
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, bgr = cap.read()
        cap.release()
        if not ok or bgr is None:
            bgr = np.zeros((224, 224, 3), dtype=np.uint8)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        return self.tf(gray3), label
