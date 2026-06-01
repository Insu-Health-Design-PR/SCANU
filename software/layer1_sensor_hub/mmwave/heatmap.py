"""2D occupancy / SNR / velocity heatmaps from normalized mmWave frames."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class HeatmapConfig:
    width_m: float = 8.0
    height_m: float = 6.0
    bins_x: int = 80
    bins_y: int = 60
    smoothing_sigma: float = 0.0
    max_range_m: float = 12.0


class HeatmapGenerator:

    def __init__(self, config: HeatmapConfig | None = None):
        self.config = config or HeatmapConfig()

    def occupancy(self, frame: Any) -> np.ndarray:
        heatmap = np.zeros((self.config.bins_y, self.config.bins_x), dtype=np.float32)
        xs, ys = self._xy(frame)
        if len(xs) == 0:
            return heatmap
        ix, iy = self._bin(xs, ys)
        np.add.at(heatmap, (iy, ix), 1)
        heatmap = (heatmap > 0).astype(np.float32)
        return self._maybe_smooth(heatmap)

    def snr_weighted(self, frame: Any) -> np.ndarray:
        heatmap = np.zeros((self.config.bins_y, self.config.bins_x), dtype=np.float32)
        xs, ys = self._xy(frame)
        if len(xs) == 0:
            return heatmap
        snrs = np.array([getattr(o, "snr", 0.0) for o in getattr(frame, "objects", [])], dtype=np.float32)
        ix, iy = self._bin(xs, ys)
        np.add.at(heatmap, (iy, ix), snrs)
        return self._maybe_smooth(heatmap)

    def velocity_magnitude(self, frame: Any) -> np.ndarray:
        heatmap = np.zeros((self.config.bins_y, self.config.bins_x), dtype=np.float32)
        xs, ys = self._xy(frame)
        if len(xs) == 0:
            return heatmap
        vels = np.abs(np.array([getattr(o, "velocity_mps", 0.0) for o in getattr(frame, "objects", [])], dtype=np.float32))
        ix, iy = self._bin(xs, ys)
        np.add.at(heatmap, (iy, ix), vels)
        return self._maybe_smooth(heatmap)

    def cumulative_occupancy(self, frames: list[Any]) -> np.ndarray:
        heatmap = np.zeros((self.config.bins_y, self.config.bins_x), dtype=np.float32)
        for f in frames:
            xs, ys = self._xy(f)
            if len(xs) == 0:
                continue
            ix, iy = self._bin(xs, ys)
            np.add.at(heatmap, (iy, ix), 1)
        heatmap = (heatmap > 0).astype(np.float32)
        return self._maybe_smooth(heatmap)

    def render(self, heatmap: np.ndarray, output_path: str | Path) -> Path:
        import cv2
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        norm = cv2.normalize(heatmap, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        colored = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
        cv2.imwrite(str(out), colored, [int(cv2.IMWRITE_PNG_COMPRESSION), 3])
        return out

    def _xy(self, frame: Any) -> tuple[np.ndarray, np.ndarray]:
        xs = np.array([getattr(o, "x", 0.0) for o in getattr(frame, "objects", [])], dtype=np.float32)
        ys = np.array([getattr(o, "y", 0.0) for o in getattr(frame, "objects", [])], dtype=np.float32)
        return xs, ys

    def _bin(self, xs: np.ndarray, ys: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        ix = np.clip(((xs + self.config.width_m / 2) / self.config.width_m * self.config.bins_x).astype(int), 0, self.config.bins_x - 1)
        iy = np.clip((ys / self.config.height_m * self.config.bins_y).astype(int), 0, self.config.bins_y - 1)
        return ix, iy

    def _maybe_smooth(self, h: np.ndarray) -> np.ndarray:
        if self.config.smoothing_sigma <= 0:
            return h
        import cv2
        sigma = max(0.5, self.config.smoothing_sigma)
        ksize = int(2 * round(sigma * 2) + 1)
        return cv2.GaussianBlur(h, (ksize, ksize), sigma)
