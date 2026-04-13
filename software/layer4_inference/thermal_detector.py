"""Drawing helpers for Layer 8 preview (boxes from ``InferenceEngine``)."""

from __future__ import annotations

from typing import Any, Sequence

import cv2
import numpy as np


def draw_detections_on_image(
    dest_bgr: np.ndarray,
    detections: Sequence[Any],
    *,
    box_source_width: int,
    box_source_height: int,
) -> None:
    """Scale boxes from source frame size onto ``dest_bgr`` and draw rectangles + scores."""
    if dest_bgr is None or dest_bgr.size == 0 or not detections:
        return
    dh, dw = dest_bgr.shape[:2]
    sw = max(int(box_source_width), 1)
    sh = max(int(box_source_height), 1)
    sx = dw / sw
    sy = dh / sh

    font = cv2.FONT_HERSHEY_SIMPLEX
    for d in detections:
        x1 = int(round(float(d.x1) * sx))
        y1 = int(round(float(d.y1) * sy))
        x2 = int(round(float(d.x2) * sx))
        y2 = int(round(float(d.y2) * sy))
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(dw - 1, x2), min(dh - 1, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        unsafe = bool(getattr(d, "unsafe", False))
        color = (0, 0, 255) if unsafe else (0, 220, 0)
        thick = 3 if unsafe else 2
        cv2.rectangle(dest_bgr, (x1, y1), (x2, y2), color, thick)
        score = float(getattr(d, "score", 0.0))
        tag = str(getattr(d, "yolo_tag", "")).strip()
        prefix = f"{tag} " if tag else ""
        txt = f"{prefix}{'UNSAFE' if unsafe else 'safe'} {score:.2f}"
        ty = max(y1 - 6, 18)
        cv2.putText(dest_bgr, txt, (x1, ty), font, 0.55, color, 2, cv2.LINE_AA)
