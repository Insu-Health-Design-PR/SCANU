"""
Train a small **safe vs unsafe** image classifier on a folder dataset produced by
:func:`collecting_data_vision.build_classify_image_dataset` (``train/safe``, ``train/unsafe``, …).

Uses ``torchvision`` (install alongside your ``torch`` build).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch.utils.data import DataLoader


def _split_has_images(root: Path, split: str) -> bool:
    for cls in ("safe", "unsafe"):
        d = root / split / cls
        if d.is_dir() and any(d.glob("*.jpg")):
            return True
    return False


def _try_torchvision():
    try:
        import torchvision
        from torchvision import datasets, transforms, models

        return torchvision, datasets, transforms, models
    except ImportError as e:
        raise ImportError(
            "safe_unsafe_cnn requires torchvision (match your torch install). "
            "See software/layer4_inference/requirements.txt"
        ) from e


def build_model(*, pretrained_backbone: bool = False, num_classes: int = 2) -> nn.Module:
    """ResNet-18 head for binary (or k-way) classification."""
    _, _, _, models = _try_torchvision()
    if pretrained_backbone:
        try:
            rw = models.ResNet18_Weights.IMAGENET1K_V1
            m = models.resnet18(weights=rw)
        except (TypeError, AttributeError):
            m = models.resnet18(pretrained=True)  # type: ignore[call-arg]
    else:
        try:
            m = models.resnet18(weights=None)
        except TypeError:
            m = models.resnet18(pretrained=False)  # type: ignore[call-arg]
    in_f = m.fc.in_features
    m.fc = nn.Linear(in_f, int(num_classes))
    return m


def _transforms_train(img_size: int):
    _, _, transforms, _ = _try_torchvision()
    return transforms.Compose(
        [
            transforms.Resize((img_size, img_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.ColorJitter(brightness=0.15, contrast=0.15),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


def _transforms_val(img_size: int):
    _, _, transforms, _ = _try_torchvision()
    return transforms.Compose(
        [
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


def _evaluate_model_on_split(
    model: nn.Module,
    split_dir: Path,
    *,
    class_to_idx: dict[str, int],
    img_size: int,
    batch_size: int,
    num_workers: int,
    dev: torch.device,
    split_name: str,
    verbose: bool = True,
) -> dict[str, Any]:
    """Confusion matrix on ``split_dir`` (ImageFolder with class subdirs)."""
    _, datasets, _, _ = _try_torchvision()
    if not split_dir.is_dir():
        raise FileNotFoundError(f"Missing split directory: {split_dir}")
    ds = datasets.ImageFolder(split_dir, transform=_transforms_val(img_size))
    if len(ds) == 0:
        raise FileNotFoundError(f"No images under {split_dir}")

    num_classes = len(class_to_idx)
    if len(ds.classes) != num_classes:
        pass  # still run; targets use ds.class_to_idx

    loader = DataLoader(
        ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=(dev.type == "cuda"),
    )

    model.eval()
    cm = torch.zeros(num_classes, num_classes, dtype=torch.int64)
    correct = 0
    n = 0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(dev, non_blocking=True)
            y = y.to(dev, non_blocking=True)
            pred = model(x).argmax(dim=1)
            correct += int((pred == y).sum().item())
            n += x.size(0)
            for i in range(y.size(0)):
                cm[int(y[i]), int(pred[i])] += 1

    acc = correct / max(1, n)
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    row_labels = [idx_to_class.get(i, str(i)) for i in range(num_classes)]

    if verbose:
        print(f"split={split_name!r}  n={n}  accuracy={acc:.4f}  classes={class_to_idx}")
        print("confusion_matrix [rows=true label, cols=pred]:")
        print(" " * 12 + "".join(f"{c:>12}" for c in row_labels))
        for i, name in enumerate(row_labels):
            print(f"{name:12}" + "".join(f"{int(v):12}" for v in cm[i].tolist()))

    return {
        "split": split_name,
        "n": n,
        "accuracy": acc,
        "confusion_matrix": cm.tolist(),
        "class_to_idx": class_to_idx,
        "row_labels": row_labels,
    }


def train_classifier(
    dataset_dir: Path | str,
    *,
    epochs: int = 30,
    batch_size: int = 16,
    lr: float = 1e-3,
    img_size: int = 224,
    num_workers: int = 2,
    pretrained_backbone: bool = False,
    device: str | None = None,
    out_weights: Path | str | None = None,
) -> dict[str, Any]:
    """
    Train on ``dataset_dir/train`` and tune on ``dataset_dir/val`` (ImageFolder layout).

    If ``dataset_dir/test`` exists (from ``build_classify_image_dataset(..., test_fraction>0)``),
    runs a final **held-out** evaluation on ``test`` and stores ``test_acc`` in the checkpoint.

    Class folder names are ordered alphabetically: ``safe`` -> 0, ``unsafe`` -> 1.
    """
    _, datasets, _, _ = _try_torchvision()
    root = Path(dataset_dir).expanduser().resolve()
    train_dir = root / "train"
    val_dir = root / "val"
    if not train_dir.is_dir() or not val_dir.is_dir():
        raise FileNotFoundError(f"Expected {train_dir} and {val_dir} (run build_classify_image_dataset first)")

    dev = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    train_ds = datasets.ImageFolder(train_dir, transform=_transforms_train(img_size))
    val_ds = datasets.ImageFolder(val_dir, transform=_transforms_val(img_size))
    if train_ds.classes != ["safe", "unsafe"]:
        # Still works; document actual order
        pass

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=(dev.type == "cuda"),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=(dev.type == "cuda"),
    )

    num_classes = len(train_ds.classes)
    model = build_model(pretrained_backbone=pretrained_backbone, num_classes=num_classes).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    crit = nn.CrossEntropyLoss()

    best_acc = 0.0
    best_state: dict[str, Any] | None = None

    for ep in range(int(epochs)):
        model.train()
        loss_tr = 0.0
        n_tr = 0
        for x, y in train_loader:
            x = x.to(dev, non_blocking=True)
            y = y.to(dev, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            logits = model(x)
            loss = crit(logits, y)
            loss.backward()
            opt.step()
            loss_tr += float(loss.item()) * x.size(0)
            n_tr += x.size(0)

        model.eval()
        correct = 0
        n_val = 0
        with torch.no_grad():
            for x, y in val_loader:
                x = x.to(dev, non_blocking=True)
                y = y.to(dev, non_blocking=True)
                pred = model(x).argmax(dim=1)
                correct += int((pred == y).sum().item())
                n_val += x.size(0)
        acc = correct / max(1, n_val)
        if acc > best_acc:
            best_acc = acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

        print(
            f"epoch {ep + 1}/{epochs}  train_loss={loss_tr / max(1, n_tr):.4f}  val_acc={acc:.4f}  "
            f"classes={train_ds.class_to_idx}"
        )

    out_path = Path(out_weights).expanduser().resolve() if out_weights else root / "safe_unsafe_cnn.pt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": "resnet18",
        "num_classes": num_classes,
        "class_to_idx": train_ds.class_to_idx,
        "img_size": img_size,
        "state_dict": best_state or model.state_dict(),
        "best_val_acc": best_acc,
    }
    test_metrics: dict[str, Any] | None = None
    if _split_has_images(root, "test"):
        print("--- held-out test (not used for training or model selection) ---")
        model.load_state_dict(best_state or model.state_dict())
        test_metrics = _evaluate_model_on_split(
            model,
            root / "test",
            class_to_idx=train_ds.class_to_idx,
            img_size=img_size,
            batch_size=batch_size,
            num_workers=num_workers,
            dev=dev,
            split_name="test",
            verbose=True,
        )
        payload["test_acc"] = test_metrics["accuracy"]
        payload["test_confusion_matrix"] = test_metrics["confusion_matrix"]

    torch.save(payload, out_path)
    print(f"saved {out_path}  best_val_acc={best_acc:.4f}")
    out_ret: dict[str, Any] = {
        "weights_path": out_path,
        "best_val_acc": best_acc,
        "class_to_idx": train_ds.class_to_idx,
    }
    if test_metrics is not None:
        out_ret["test_metrics"] = test_metrics
    return out_ret


def evaluate_classifier(
    weights_path: Path | str,
    dataset_dir: Path | str,
    *,
    split: str = "test",
    batch_size: int = 16,
    img_size: int | None = None,
    num_workers: int = 2,
    device: str | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Load ``safe_unsafe_cnn.pt`` and report accuracy + confusion matrix on ``val`` or ``test``.

    Use **test** for an unbiased score only if that split was held out during training.
    """
    wp = Path(weights_path).expanduser().resolve()
    root = Path(dataset_dir).expanduser().resolve()
    split_dir = root / split
    if not split_dir.is_dir():
        raise FileNotFoundError(f"Missing split directory: {split_dir}")

    dev = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    try:
        ckpt = torch.load(str(wp), map_location="cpu", weights_only=False)
    except TypeError:
        ckpt = torch.load(str(wp), map_location="cpu")
    if not isinstance(ckpt, dict) or "state_dict" not in ckpt:
        raise ValueError(f"Not a safe_unsafe_cnn checkpoint: {wp}")
    class_to_idx: dict[str, int] = ckpt.get("class_to_idx") or {"safe": 0, "unsafe": 1}
    num_classes = int(ckpt.get("num_classes") or len(class_to_idx))
    img_size = int(img_size if img_size is not None else ckpt.get("img_size") or 224)

    model = build_model(pretrained_backbone=False, num_classes=num_classes).to(dev)
    model.load_state_dict(ckpt["state_dict"], strict=True)

    return _evaluate_model_on_split(
        model,
        split_dir,
        class_to_idx=class_to_idx,
        img_size=img_size,
        batch_size=batch_size,
        num_workers=num_workers,
        dev=dev,
        split_name=split,
        verbose=verbose,
    )
