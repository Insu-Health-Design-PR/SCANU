"""Thermal object/threat detector wrapper for Layer 4."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
from PIL import Image


def ml_stack_error_hint(*, cause: BaseException | None = None) -> str:
    """
    Human-readable hint when HF/transformers/torch are missing or version-incompatible
    (common on Jetson: apt torch 1.8 + pip transformers 5.x).
    """
    torch_v = "?"
    try:
        import torch

        torch_v = str(getattr(torch, "__version__", "?"))
    except Exception:
        torch_v = "(import failed)"

    tf_v = "?"
    try:
        import transformers

        tf_v = str(getattr(transformers, "__version__", "?"))
    except Exception:
        tf_v = "(import failed)"

    tail = (
        "Typical fix on Jetson: either install NVIDIA's PyTorch wheel for your JetPack, "
        "or pin Transformers 4.x so it matches your torch: "
        "pip install --user --force-reinstall 'transformers>=4.43,<5'. "
        "See software/layer4_inference/requirements.txt."
    )
    if cause is not None:
        return f"Layer 4 ML backend failed ({cause}). torch={torch_v!r}, transformers={tf_v!r}. {tail}"
    return f"torch={torch_v!r}, transformers={tf_v!r}. {tail}"


@dataclass(frozen=True, slots=True)
class Detection:
    """One model detection."""

    label: str
    score: float
    xmin: float
    ymin: float
    xmax: float
    ymax: float


class ThermalThreatDetector:
    """
    Lazy-loaded thermal detector using an existing pretrained model.

    Default model is a thermal object detector hosted on Hugging Face.
    """

    # Hugging Face object-detection checkpoint for ``pipeline("object-detection", ...)``.
    # The older ``falconsai/thermal-imaging-object-detection`` repo often returns 401 /
    # is unavailable without a token; override via settings ``thermal_inference_model_id``
    # or constructor ``model_id=`` when you have a working thermal checkpoint.
    DEFAULT_MODEL_ID = "facebook/detr-resnet-50"

    def __init__(self, model_id: str | None = None, *, threshold: float = 0.25, device: int = -1) -> None:
        self.model_id = model_id or self.DEFAULT_MODEL_ID
        self.threshold = float(threshold)
        self.device = int(device)
        self._pipe: Any | None = None

    def _ensure_loaded(self) -> None:
        if self._pipe is not None:
            return
        try:
            from transformers import pipeline

            self._pipe = pipeline(
                "object-detection",
                model=self.model_id,
                device=self.device,
            )
        except Exception as exc:  # pragma: no cover - dependency/runtime path
            raise RuntimeError(ml_stack_error_hint(cause=exc)) from exc

    def detect(self, frame_bgr) -> list[Detection]:
        """Run detection on one BGR frame and return normalized results."""
        self._ensure_loaded()
        if frame_bgr is None:
            return []

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        # Transformers 5 image pipelines expect PIL, URL, or base64 — not raw ndarray.
        pil = Image.fromarray(rgb)
        outputs = self._pipe(pil, threshold=self.threshold)
        detections: list[Detection] = []
        for det in outputs:
            box = det.get("box") or {}
            detections.append(
                Detection(
                    label=str(det.get("label", "unknown")).lower(),
                    score=float(det.get("score", 0.0)),
                    xmin=float(box.get("xmin", 0.0)),
                    ymin=float(box.get("ymin", 0.0)),
                    xmax=float(box.get("xmax", 0.0)),
                    ymax=float(box.get("ymax", 0.0)),
                )
            )
        return detections


def draw_detections_on_image(
    image_bgr,
    detections: list[Detection],
    *,
    box_source_width: int,
    box_source_height: int,
    color: tuple[int, int, int] = (0, 255, 100),
    thickness: int = 2,
) -> None:
    """Draw labeled boxes on ``image_bgr``. Box coords are in ``box_source_*`` pixel space."""
    if image_bgr is None or image_bgr.size == 0:
        return
    h, w = image_bgr.shape[:2]
    sw = max(1, int(box_source_width))
    sh = max(1, int(box_source_height))
    sx = w / sw
    sy = h / sh
    for d in detections:
        x1 = int(round(float(d.xmin) * sx))
        y1 = int(round(float(d.ymin) * sy))
        x2 = int(round(float(d.xmax) * sx))
        y2 = int(round(float(d.ymax) * sy))
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        cv2.rectangle(image_bgr, (x1, y1), (x2, y2), color, thickness, lineType=cv2.LINE_AA)
        label = f"{d.label} {d.score:.2f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        fs = 0.5
        (tw, th), _ = cv2.getTextSize(label, font, fs, 1)
        pad = 4
        ty0 = max(0, y1 - th - pad * 2)
        cv2.rectangle(image_bgr, (x1, ty0), (x1 + tw + pad, y1), color, -1, lineType=cv2.LINE_AA)
        cv2.putText(
            image_bgr,
            label,
            (x1 + pad // 2, y1 - pad),
            font,
            fs,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )

