"""
Live **safe / unsafe** classification from a BGR image (Layer 8 thermal preview overlay).

Uses checkpoints saved by :func:`layer4_inference.safe_unsafe_cnn.train_classifier`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image


def _val_transform(img_size: int):
    from torchvision import transforms

    return transforms.Compose(
        [
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


def load_safe_unsafe_classifier(
    weights_path: Path | str,
    *,
    device: torch.device | None = None,
) -> tuple[nn.Module, dict[str, Any], Any]:
    """
    Load ``best.pt`` / ``safe_unsafe_cnn.pt`` for inference.

    Returns ``(model, meta, transform)`` where ``meta`` has ``img_size`` and ``class_to_idx``.
    """
    wp = Path(weights_path).expanduser().resolve()
    if not wp.is_file():
        raise FileNotFoundError(str(wp))
    dev = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        ckpt = torch.load(str(wp), map_location="cpu", weights_only=False)
    except TypeError:
        ckpt = torch.load(str(wp), map_location="cpu")
    if not isinstance(ckpt, dict) or "state_dict" not in ckpt:
        raise ValueError(f"Not a CNN classifier checkpoint: {wp}")

    from layer4_inference.safe_unsafe_cnn import build_model

    nclass = int(ckpt.get("num_classes") or 2)
    model = build_model(pretrained_backbone=False, num_classes=nclass)
    model.load_state_dict(ckpt["state_dict"], strict=True)
    model.to(dev).eval()
    meta: dict[str, Any] = {
        "img_size": int(ckpt.get("img_size") or 224),
        "class_to_idx": dict(ckpt.get("class_to_idx") or {"safe": 0, "unsafe": 1}),
    }
    return model, meta, _val_transform(meta["img_size"])


@torch.inference_mode()
def predict_safe_unsafe(
    model: nn.Module,
    meta: dict[str, Any],
    tfm: Any,
    bgr: np.ndarray,
    *,
    device: torch.device,
) -> tuple[str, float, dict[str, float]]:
    """
    Predict from a BGR ``uint8`` image (e.g. thermal colormap or composite hub frame).

    Returns ``(label, confidence_for_label, probs_by_class_name)``.
    """
    if bgr is None or bgr.size == 0:
        return "?", 0.0, {}
    if bgr.ndim == 2:
        bgr = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    x = tfm(pil).unsqueeze(0).to(device)
    logits = model(x)
    prob = torch.softmax(logits, dim=1)[0]
    idx = int(prob.argmax().item())
    idx_to_name = {v: k for k, v in meta["class_to_idx"].items()}
    name = idx_to_name.get(idx, str(idx))
    conf = float(prob[idx].item())
    all_p = {idx_to_name.get(i, str(i)): float(prob[i].item()) for i in range(len(prob))}
    return name, conf, all_p
