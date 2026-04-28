"""
Thermal camera helpers for Layer 1.

Provides a small reusable wrapper around OpenCV V4L2 capture so examples can
consume thermal frames consistently in headless mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


def normalize_thermal_frame(frame: np.ndarray) -> np.ndarray:
    """Normalize 16-bit/8-bit thermal frame to uint8 grayscale."""

    if frame.dtype == np.uint16:
        f32 = frame.astype(np.float32)
        mn = float(np.min(f32))
        mx = float(np.max(f32))
        if mx - mn < 1e-6:
            return np.zeros_like(frame, dtype=np.uint8)
        f32 = (f32 - mn) / (mx - mn)
        return (f32 * 255.0).astype(np.uint8)

    if frame.dtype != np.uint8:
        frame = frame.astype(np.uint8)

    if frame.ndim == 3 and frame.shape[2] >= 1:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return frame


@dataclass(frozen=True, slots=True)
class ThermalFrameInfo:
    width: int
    height: int
    fps: float


class ThermalCameraSource:
    """Small V4L2 thermal source wrapper for examples."""

    def __init__(
        self,
        device: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
    ) -> None:
        self._cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open thermal camera /dev/video{device}")

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._cap.set(cv2.CAP_PROP_FPS, fps)

    def info(self) -> ThermalFrameInfo:
        return ThermalFrameInfo(
            width=int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=float(self._cap.get(cv2.CAP_PROP_FPS)),
        )

    def read_raw(self) -> Optional[np.ndarray]:
        ok, frame = self._cap.read()
        if not ok:
            return None
        return frame

    def read_colormap_bgr(self) -> Optional[np.ndarray]:
        frame = self.read_raw()
        if frame is None:
            return None
        gray = normalize_thermal_frame(frame)
        return cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()

