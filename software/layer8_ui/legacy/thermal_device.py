"""Thermal camera device auto-detection helpers."""

from __future__ import annotations

import os

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import cv2


def _probe_device(index: int, width: int, height: int, fps: int) -> bool:
    cap = cv2.VideoCapture(int(index), cv2.CAP_V4L2)
    if not cap.isOpened():
        return False
    try:
        cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("Y", "1", "6", " "))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
        cap.set(cv2.CAP_PROP_FPS, int(fps))
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        ok, frame = cap.read()
        return bool(ok and frame is not None)
    finally:
        cap.release()


def detect_working_thermal_device(
    *,
    preferred: int,
    width: int,
    height: int,
    fps: int,
    search_max_index: int = 6,
) -> int | None:
    """
    Return first working V4L2 index for thermal capture.

    Strategy:
    1) Try preferred index first.
    2) Fallback scan from 0..search_max_index excluding preferred.
    """
    if preferred >= 0 and _probe_device(preferred, width, height, fps):
        return preferred

    for idx in range(0, int(search_max_index) + 1):
        if idx == preferred:
            continue
        if _probe_device(idx, width, height, fps):
            return idx
    return None

