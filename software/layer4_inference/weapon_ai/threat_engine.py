"""Single-frame thermal threat inference (same stack as ``infer_thermal_objects``).

Used by Layer 5 fusion; Layer 8 demo uses ``weapon_ai.webcam_layer8_runner`` + subprocess.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import cv2
import numpy as np
import torch
from torchvision import transforms
from ultralytics import YOLO

from .infer_thermal_objects import (
    _DEFAULT_FIREARM_YOLO,
    _clamp_box,
    _ensure_firearm_yolo_weights,
    _expand_person_roi_for_gun,
    _gun_detection_valid,
    _parse_yolo_classes,
)
from .modeling import build_model


_L4_ROOT = Path(__file__).resolve().parent.parent

_MODEL_FILES: dict[str, Path] = {
    "gun_prob_default": _L4_ROOT / "trained_models" / "gun_detection" / "gun_prob_best.pt",
    "gun_prob_smoke": _L4_ROOT / "trained_models" / "gun_detection" / "gun_prob_smoke_best.pt",
}


def _resolve_checkpoint(model_id: str) -> Path:
    mid = (model_id or "").strip()
    if not mid:
        mid = "gun_prob_default"
    p = Path(mid).expanduser()
    if p.is_file():
        return p.resolve()
    key = mid if mid in _MODEL_FILES else "gun_prob_default"
    return _MODEL_FILES[key].resolve()


@dataclass(frozen=True)
class ThreatDetection:
    """One person-box threat estimate in source image coordinates."""

    x1: int
    y1: int
    x2: int
    y2: int
    score: float
    yolo_tag: str
    unsafe: bool

    @property
    def label_text(self) -> str:
        return f"{'UNSAFE' if self.unsafe else 'safe'} {self.score:.2f}"


@dataclass(frozen=True)
class InferenceResult:
    frame_number: int
    timestamp_ms: float
    detections: tuple[ThreatDetection, ...]
    frame_max_score: float


@dataclass(frozen=True)
class AnomalyDecision:
    """Layer-4 semantic label for fusion (armed ~= confirmed threat on thermal)."""

    label: str  # unarmed | suspicious | armed
    anomaly_score: float
    confidence: float


class ThermalThreatDetector:
    """Loads YOLO + crop classifier (+ optional firearm YOLO) for one-frame thermal infer."""

    DEFAULT_MODEL_ID = "gun_prob_default"

    def __init__(
        self,
        *,
        model_id: str | None = None,
        threshold: float = 0.5,
        device: int = -1,
        yolo_model: str | Path | None = None,
        image_size: int = 224,
        yolo_conf: float = 0.25,
        min_box_px: int = 24,
        fuse_gun_to_prob: bool = True,
        gun_prob_floor: float = 0.60,
        gun_conf_scale: float = 2.0,
        gun_take_best: bool = True,
        gun_conf: float = 0.25,
        gun_max_area_frac: float = 0.22,
        gun_max_side_frac: float = 0.65,
        gun_min_box_px: int = 8,
        gun_imgsz: int = 640,
        gun_roi_pad_frac: float = 0.06,
        gun_roi_pad_px: int = 8,
        gun_full_frame: bool = False,
        gun_yolo_model: Path | None = None,
    ) -> None:
        self.unsafe_threshold = float(threshold)
        self._image_size = int(image_size)
        self._yolo_conf = float(yolo_conf)
        self._min_box_px = int(min_box_px)
        self._fuse_gun_to_prob = bool(fuse_gun_to_prob)
        self._gun_prob_floor = float(gun_prob_floor)
        self._gun_conf_scale = float(gun_conf_scale)
        self._gun_take_best = bool(gun_take_best)
        self._gun_conf = float(gun_conf)
        self._gun_max_area_frac = float(gun_max_area_frac)
        self._gun_max_side_frac = float(gun_max_side_frac)
        self._gun_min_box_px = int(gun_min_box_px)
        self._gun_imgsz = int(gun_imgsz)
        self._gun_roi_pad_frac = float(gun_roi_pad_frac)
        self._gun_roi_pad_px = int(gun_roi_pad_px)
        self._gun_full_frame = bool(gun_full_frame)

        ck_path = _resolve_checkpoint(model_id or self.DEFAULT_MODEL_ID)
        if not ck_path.is_file():
            raise FileNotFoundError(f"Checkpoint not found: {ck_path}")

        use_cuda = device >= 0 and torch.cuda.is_available()
        self._device = torch.device(f"cuda:{int(device)}" if use_cuda else "cpu")
        self._det_device = 0 if use_cuda else "cpu"

        ck = torch.load(ck_path, map_location="cpu", weights_only=False)
        arch = str(ck.get("arch", "mobilenet_v3_small"))
        is_gun_prob = (
            ck.get("objective") == "gun_prob_bce"
            or ck.get("video_mode") == "gun_prob"
            or int(ck.get("num_classes", 2)) == 1
        )
        self._is_gun_prob = bool(is_gun_prob)
        self._infer_gray3 = str(ck.get("preprocess", "")).startswith("gray3ch")

        clf = build_model(arch, num_classes=1 if is_gun_prob else 2).to(self._device)
        clf.load_state_dict(ck["model"])
        clf.eval()
        self._clf = clf

        self._tf = transforms.Compose(
            [
                transforms.ToPILImage(),
                transforms.Resize((self._image_size, self._image_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

        ypath = Path(yolo_model).expanduser() if yolo_model else (_L4_ROOT / "yolov8n.pt")
        if not ypath.is_file():
            raise FileNotFoundError(f"YOLO weights not found: {ypath}")
        self._person_yolo = YOLO(str(ypath.resolve()))
        self._yolo_classes = _parse_yolo_classes("0")

        gpath = gun_yolo_model if gun_yolo_model is not None else _DEFAULT_FIREARM_YOLO
        gpath = Path(gpath).resolve()
        _ensure_firearm_yolo_weights(gpath)
        self._gun_yolo: YOLO | None = YOLO(str(gpath))

    def infer_bgr(self, thermal_bgr: np.ndarray) -> tuple[ThreatDetection, ...]:
        """Run person crops + classifier (+ optional gun YOLO) on one BGR thermal frame."""
        if thermal_bgr is None or thermal_bgr.size == 0:
            return ()

        thermal = thermal_bgr
        h, w = thermal.shape[:2]

        pred_kw: dict[str, Any] = dict(
            source=thermal,
            conf=self._yolo_conf,
            verbose=False,
            device=self._det_device,
        )
        if self._yolo_classes is not None:
            pred_kw["classes"] = self._yolo_classes

        results = self._person_yolo.predict(**pred_kw)
        boxes = results[0].boxes if results else None
        id_to_name = results[0].names if results and hasattr(results[0], "names") else {}

        rows: list[tuple[int, int, int, int, float, int | None, str]] = []

        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy()
            cls_ids = boxes.cls.cpu().numpy().astype(int) if boxes.cls is not None else None
            with torch.no_grad():
                for i, row in enumerate(xyxy):
                    x1, y1, x2, y2 = _clamp_box(row, w, h)
                    if (x2 - x1) < self._min_box_px or (y2 - y1) < self._min_box_px:
                        continue
                    crop_bgr = thermal[y1:y2, x1:x2]
                    if crop_bgr.size == 0:
                        continue
                    if crop_bgr.ndim == 2:
                        crop_bgr = cv2.cvtColor(crop_bgr, cv2.COLOR_GRAY2BGR)
                    if self._infer_gray3:
                        gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
                        in_rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
                    else:
                        in_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
                    x = self._tf(in_rgb).unsqueeze(0).to(self._device)
                    logits = self._clf(x)
                    if self._is_gun_prob:
                        prob = float(torch.sigmoid(logits.reshape(-1))[0].item())
                    else:
                        prob = float(torch.softmax(logits, dim=1)[0, 1].item())
                    cid = int(cls_ids[i]) if cls_ids is not None and i < len(cls_ids) else None
                    yolo_tag = id_to_name.get(cid, str(cid)) if cid is not None else "obj"
                    rows.append((x1, y1, x2, y2, prob, cid, yolo_tag))

        gun_count = 0
        frame_gun_best_conf = 0.0
        if self._gun_yolo is not None:
            infer_gun_conf = min(float(self._gun_conf), 0.01) if self._gun_take_best else float(self._gun_conf)

            def _emit_firearm_overlay(gx1: int, gy1: int, gx2: int, gy2: int, gc: float) -> None:
                nonlocal gun_count, frame_gun_best_conf
                gx1, gy1, gx2, gy2 = max(0, gx1), max(0, gy1), min(w, gx2), min(h, gy2)
                gun_count += 1
                frame_gun_best_conf = max(frame_gun_best_conf, float(gc))

            def _draw_gun_from_candidates(
                candidates: list[tuple[float, int, int, int, int]],
                pr: int,
                pb: int,
            ) -> None:
                if not candidates:
                    return
                normed: list[tuple[float, int, int, int, int]] = []
                for gc, gx1, gy1, gx2, gy2 in candidates:
                    gx1, gy1, gx2, gy2 = max(0, gx1), max(0, gy1), min(w, gx2), min(h, gy2)
                    normed.append((gc, gx1, gy1, gx2, gy2))
                if self._gun_take_best:
                    for gc, gx1, gy1, gx2, gy2 in sorted(normed, key=lambda t: -t[0]):
                        if _gun_detection_valid(
                            gx1,
                            gy1,
                            gx2,
                            gy2,
                            w,
                            h,
                            self._gun_max_area_frac,
                            self._gun_max_side_frac,
                            self._gun_min_box_px,
                            ref_w=pr,
                            ref_h=pb,
                        ):
                            _emit_firearm_overlay(gx1, gy1, gx2, gy2, gc)
                            return
                    return
                for gc, gx1, gy1, gx2, gy2 in normed:
                    if not _gun_detection_valid(
                        gx1,
                        gy1,
                        gx2,
                        gy2,
                        w,
                        h,
                        self._gun_max_area_frac,
                        self._gun_max_side_frac,
                        self._gun_min_box_px,
                        ref_w=pr,
                        ref_h=pb,
                    ):
                        continue
                    _emit_firearm_overlay(gx1, gy1, gx2, gy2, gc)

            if self._gun_full_frame:
                gres = self._gun_yolo.predict(
                    source=thermal,
                    conf=infer_gun_conf,
                    imgsz=self._gun_imgsz,
                    verbose=False,
                    device=self._det_device,
                )
                gboxes = gres[0].boxes if gres else None
                candidates_ff: list[tuple[float, int, int, int, int]] = []
                if gboxes is not None and len(gboxes) > 0:
                    g_xyxy = gboxes.xyxy.cpu().numpy()
                    g_conf = gboxes.conf.cpu().numpy() if gboxes.conf is not None else None
                    for j, grow in enumerate(g_xyxy):
                        gx1, gy1, gx2, gy2 = _clamp_box(grow, w, h)
                        gc = float(g_conf[j]) if g_conf is not None and j < len(g_conf) else 0.0
                        candidates_ff.append((gc, gx1, gy1, gx2, gy2))
                _draw_gun_from_candidates(candidates_ff, w, h)
            elif rows:
                for px1, py1, px2, py2, _prob, pcid, _ptag in rows:
                    if pcid is not None and pcid != 0:
                        continue
                    qx1, qy1, qx2, qy2 = _expand_person_roi_for_gun(
                        px1,
                        py1,
                        px2,
                        py2,
                        w,
                        h,
                        self._gun_roi_pad_frac,
                        int(self._gun_roi_pad_px),
                    )
                    pr, pb = qx2 - qx1, qy2 - qy1
                    if pr < self._min_box_px or pb < self._min_box_px:
                        continue
                    pcrop = thermal[qy1:qy2, qx1:qx2]
                    if pcrop.size == 0:
                        continue
                    gres = self._gun_yolo.predict(
                        source=pcrop,
                        conf=infer_gun_conf,
                        imgsz=self._gun_imgsz,
                        verbose=False,
                        device=self._det_device,
                    )
                    gboxes = gres[0].boxes if gres else None
                    candidates_roi: list[tuple[float, int, int, int, int]] = []
                    if gboxes is not None and len(gboxes) > 0:
                        g_xyxy = gboxes.xyxy.cpu().numpy()
                        g_conf = gboxes.conf.cpu().numpy() if gboxes.conf is not None else None
                        cw, ch = pcrop.shape[1], pcrop.shape[0]
                        for j, grow in enumerate(g_xyxy):
                            lx1, ly1, lx2, ly2 = _clamp_box(grow, cw, ch)
                            gx1, gy1 = qx1 + lx1, qy1 + ly1
                            gx2, gy2 = qx1 + lx2, qy1 + ly2
                            gc = float(g_conf[j]) if g_conf is not None and j < len(g_conf) else 0.0
                            candidates_roi.append((gc, gx1, gy1, gx2, gy2))
                    _draw_gun_from_candidates(candidates_roi, pr, pb)

        if self._fuse_gun_to_prob and gun_count > 0 and rows:
            gun_boost = max(
                self._gun_prob_floor,
                min(0.99, frame_gun_best_conf * self._gun_conf_scale),
            )
            rows = [
                (x1, y1, x2, y2, max(prob, gun_boost), cid, ytag) for (x1, y1, x2, y2, prob, cid, ytag) in rows
            ]

        out: list[ThreatDetection] = []
        for x1, y1, x2, y2, prob, _cid, ytag in rows:
            unsafe = prob >= self.unsafe_threshold
            out.append(
                ThreatDetection(
                    x1=int(x1),
                    y1=int(y1),
                    x2=int(x2),
                    y2=int(y2),
                    score=float(prob),
                    yolo_tag=str(ytag),
                    unsafe=unsafe,
                )
            )
        return tuple(out)


class InferenceEngine:
    """Thin wrapper so callers can hold a detector and run `infer(...)` per frame."""

    def __init__(self, *, detector: ThermalThreatDetector) -> None:
        self._det = detector

    def infer(
        self,
        frame_number: int,
        timestamp_ms: float,
        thermal_frame_bgr: np.ndarray,
    ) -> InferenceResult:
        dets = self._det.infer_bgr(thermal_frame_bgr)
        mx = max((d.score for d in dets), default=0.0)
        return InferenceResult(
            frame_number=int(frame_number),
            timestamp_ms=float(timestamp_ms),
            detections=dets,
            frame_max_score=float(mx),
        )


class AnomalyScorer:
    """Maps raw crop scores to discrete labels for Layer 5 fusion."""

    def __init__(
        self,
        *,
        suspicious_threshold: float = 0.25,
        armed_threshold: float = 0.55,
        min_confidence: float = 0.20,
    ) -> None:
        self.suspicious_threshold = float(suspicious_threshold)
        self.armed_threshold = float(armed_threshold)
        self.min_confidence = float(min_confidence)

    def evaluate(self, ir: InferenceResult) -> AnomalyDecision:
        score = float(ir.frame_max_score)
        if score < self.min_confidence:
            return AnomalyDecision(label="unarmed", anomaly_score=score, confidence=score)
        if score >= self.armed_threshold:
            return AnomalyDecision(label="armed", anomaly_score=score, confidence=score)
        if score >= self.suspicious_threshold:
            return AnomalyDecision(label="suspicious", anomaly_score=score, confidence=score)
        return AnomalyDecision(label="unarmed", anomaly_score=score, confidence=score)
