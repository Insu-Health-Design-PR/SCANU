from __future__ import annotations

import torch.nn as nn
from torchvision import models


def build_model(arch: str, num_classes: int = 2) -> nn.Module:
    arch = arch.lower()
    if arch == "resnet18":
        w = models.ResNet18_Weights.IMAGENET1K_V1
        m = models.resnet18(weights=w)
        m.fc = nn.Linear(m.fc.in_features, num_classes)
        return m
    if arch == "mobilenet_v3_small":
        w = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1
        m = models.mobilenet_v3_small(weights=w)
        m.classifier[3] = nn.Linear(m.classifier[3].in_features, num_classes)
        return m
    raise ValueError(f"Unknown arch: {arch}. Use resnet18 or mobilenet_v3_small.")


def build_gun_prob_model(arch: str) -> nn.Module:
    """Single-logit BCE head for P(gun)."""
    return build_model(arch, num_classes=1)
