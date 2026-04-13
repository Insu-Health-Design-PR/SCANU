"""
Thermal camera helpers for Layer 1.

Provides a small reusable wrapper around OpenCV V4L2 capture so examples can
consume thermal frames consistently in headless mode.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

# Cut OpenCV spam when open fails (e.g. device busy); must run before cv2 import.
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

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
        *,
        open_retries: int = 10,
        open_retry_delay_s: float = 0.25,
    ) -> None:
        self._cap = None
        cap: cv2.VideoCapture | None = None
        for attempt in range(max(1, int(open_retries))):
            cap = cv2.VideoCapture(int(device), cv2.CAP_V4L2)
            if cap.isOpened():
                self._cap = cap
                break
            if cap is not None:
                cap.release()
            time.sleep(max(0.05, float(open_retry_delay_s)))

        if self._cap is None or not self._cap.isOpened():
            hint = (
                " Typical causes: (1) Another process already opened this device — close any browser tab "
                "showing Layer 8 live thermal (/api/preview/live_direct/thermal) or other camera apps, "
                "then retry. (2) Wrong index — set thermal_device or enable thermal_auto_detect. "
                "(3) USB/cable or permissions (user in group 'video')."
            )
            raise RuntimeError(f"Cannot open thermal camera /dev/video{int(device)} after {open_retries} tries.{hint}")

        # Thermal sensors on V4L2 often expose grayscale/Y16 streams; forcing
        # a compatible path reduces blank/timeout frames.
        self._cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("Y", "1", "6", " "))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._cap.set(cv2.CAP_PROP_FPS, fps)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def info(self) -> ThermalFrameInfo:
        return ThermalFrameInfo(
            width=int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=float(self._cap.get(cv2.CAP_PROP_FPS)),
        )

    def read_raw(self) -> Optional[np.ndarray]:
        # Retry a few short reads before reporting no-frame.
        for _ in range(4):
            ok, frame = self._cap.read()
            if ok and frame is not None:
                return frame
        return None

    def read_colormap_bgr(self) -> Optional[np.ndarray]:
        frame = self.read_raw()
        if frame is None:
            return None
        gray = normalize_thermal_frame(frame)
        return cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()

