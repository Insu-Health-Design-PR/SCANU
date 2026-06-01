"""
Thermal camera helpers for Layer 1.

Provides a small reusable wrapper around OpenCV V4L2 capture so examples can
consume thermal frames consistently in headless mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

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


def _is_numeric_device(device: Union[int, str]) -> bool:
    if isinstance(device, int):
        return True
    try:
        int(device)
        return True
    except (ValueError, TypeError):
        return False


def _open_capture(
    device: Union[int, str],
    width: int,
    height: int,
    fps: int,
    open_retries: int,
    open_retry_delay_s: float,
) -> cv2.VideoCapture:
    import time

    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"Y16 "))
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    for attempt in range(1, open_retries + 1):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        if cap.isOpened():
            return cap
        if attempt < open_retries:
            time.sleep(open_retry_delay_s)
            cap.open(device, cv2.CAP_V4L2)

    raise RuntimeError(f"Cannot open thermal camera {device}")


def _display_device(device: Union[int, str]) -> str:
    if isinstance(device, int):
        return f"/dev/video{device}"
    if "/" not in device:
        return f"/dev/video{device}"
    return str(device)


@dataclass(frozen=True)
class ThermalFrameInfo:
    width: int
    height: int
    fps: float


class ThermalCameraSource:
    """V4L2 thermal source wrapper with robust retry logic."""

    def __init__(
        self,
        device: Union[int, str] = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        open_retries: int = 10,
        open_retry_delay_s: float = 0.25,
        read_retries: int = 4,
    ) -> None:
        self._device = device
        self._width = width
        self._height = height
        self._fps = fps
        self._read_retries = read_retries
        self._cap = _open_capture(device, width, height, fps, open_retries, open_retry_delay_s)

    def __enter__(self) -> ThermalCameraSource:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def info(self) -> ThermalFrameInfo:
        return ThermalFrameInfo(
            width=int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=float(self._cap.get(cv2.CAP_PROP_FPS)),
        )

    def read_raw(self) -> Optional[np.ndarray]:
        for _ in range(self._read_retries):
            ok, frame = self._cap.read()
            if ok:
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

    def save_raw(self, path: Union[str, Path]) -> Path:
        frame = self.read_raw()
        if frame is None:
            raise RuntimeError("No thermal frame to save")
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out), frame)
        return out
