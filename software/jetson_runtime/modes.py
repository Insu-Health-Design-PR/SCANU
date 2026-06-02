"""Layer activation contract for Jetson runtime modes."""

from __future__ import annotations

from typing import Literal

RuntimeMode = Literal["serve", "local"]

JETSON_MODE_LAYERS: dict[RuntimeMode, tuple[int, ...]] = {
    "serve": (1, 2, 3, 8),
    "local": (1, 2, 3, 4, 5, 6, 7, 8),
}


def mode_layers(mode: RuntimeMode) -> tuple[int, ...]:
    """Return the active SCANU layers for a Jetson mode."""

    return JETSON_MODE_LAYERS[mode]


def mode_description(mode: RuntimeMode) -> str:
    if mode == "serve":
        return "prepare Layer 1-3 data and send it through Layer 8 to Main"
    return "run Layers 1-8 locally on this Jetson"
