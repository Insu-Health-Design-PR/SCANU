from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset
from torchvision import transforms

from .manifest import ManifestRow


def _frame_count(cap: cv2.VideoCapture) -> int:
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if n > 0:
        return n
    # Some codecs report 0; count manually
    cur = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    count = 0
    while True:
        ok, _ = cap.read()
        if not ok:
            break
        count += 1
    cap.set(cv2.CAP_PROP_POS_FRAMES, cur)
    return max(count, 1)


class CompositeVideoFrameDataset(Dataset):
    """
    Each __getitem__ returns one RGB frame from a composite recording
    (thermal | mmwave | presence), using fixed evenly-spaced indices per video.
    """

    def __init__(
        self,
        rows: list[ManifestRow],
        frames_per_video: int,
        image_size: int = 224,
        augment: bool = False,
        crop_mode: str = "full",
    ) -> None:
        if crop_mode not in ("full", "left_third", "center_third"):
            raise ValueError(crop_mode)
        self.crop_mode = crop_mode
        self.augment = augment
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
                self.samples.append((r.video, int(fi), r.label_id))

        t_list = [
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
        t_list.append(transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]))
        self.tf = transforms.Compose(t_list)

    def __len__(self) -> int:
        return len(self.samples)

    def _crop_panel(self, bgr: np.ndarray) -> np.ndarray:
        h, w = bgr.shape[:2]
        if self.crop_mode == "full":
            return bgr
        if self.crop_mode == "left_third":
            x1, x2 = 0, w // 3
        else:
            x1, x2 = w // 3, 2 * w // 3
        return bgr[:, x1:x2]

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        path, frame_idx, label = self.samples[i]
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {path}")
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, bgr = cap.read()
        cap.release()
        if not ok or bgr is None:
            black = np.zeros((224, 224, 3), dtype=np.uint8)
            x = self.tf(black)
            return x, label
        bgr = self._crop_panel(bgr)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        x = self.tf(rgb)
        return x, label
