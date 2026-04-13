"""
Person-ROI firearm YOLO stats on a thermal/rgb video (matches infer_thermal_objects --gun_thermal + take_best).

Usage (from repo root):
  python scripts/bench_gun_yolo_roi.py --video path.mp4 --gun_pt trained_models/gun_detection/gun_rgb_subh775_best.pt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import cv2
import numpy as np
from ultralytics import YOLO

from weapon_ai.infer_thermal_objects import (
    _clamp_box,
    _expand_xyxy_frac,
    _gun_detection_valid,
)


def _pick_best_gun(
    gboxes,
    gnames: dict,
    qx1: int,
    qy1: int,
    fw: int,
    fh: int,
    pcrop_w: int,
    pcrop_h: int,
    pr: int,
    pb: int,
    infer_conf: float,
    max_area_frac: float,
    max_side_frac: float,
    gun_min_box_px: int,
) -> tuple[float, int, int, int, int, str] | None:
    if gboxes is None or len(gboxes) == 0:
        return None
    g_xyxy = gboxes.xyxy.cpu().numpy()
    g_cls = gboxes.cls.cpu().numpy().astype(int) if gboxes.cls is not None else None
    g_conf = gboxes.conf.cpu().numpy() if gboxes.conf is not None else None
    candidates: list[tuple[float, int, int, int, int, str]] = []
    for j, grow in enumerate(g_xyxy):
        lx1, ly1, lx2, ly2 = _clamp_box(grow, pcrop_w, pcrop_h)
        gx1, gy1 = qx1 + lx1, qy1 + ly1
        gx2, gy2 = qx1 + lx2, qy1 + ly2
        cid = int(g_cls[j]) if g_cls is not None and j < len(g_cls) else 0
        gnm = gnames.get(cid, "gun")
        gc = float(g_conf[j]) if g_conf is not None and j < len(g_conf) else 0.0
        if gc < infer_conf:
            continue
        candidates.append((gc, gx1, gy1, gx2, gy2, gnm))
    for gc, gx1, gy1, gx2, gy2, gnm in sorted(candidates, key=lambda t: -t[0]):
        if _gun_detection_valid(
            gx1,
            gy1,
            gx2,
            gy2,
            fw,
            fh,
            max_area_frac=max_area_frac,
            max_side_frac=max_side_frac,
            gun_min_box_px=gun_min_box_px,
            ref_w=pr,
            ref_h=pb,
        ):
            return (gc, gx1, gy1, gx2, gy2, gnm)
    return None


def run_bench(
    video: Path,
    gun_pt: Path,
    *,
    person_conf: float,
    min_person_px: int,
    gun_roi_pad_frac: float,
    gun_imgsz: int,
    max_area_frac: float,
    max_side_frac: float,
    gun_min_box_px: int,
    take_best_infer_conf: float,
    max_frames: int,
    person_yolo: str,
) -> dict:
    person = YOLO(person_yolo)
    gun = YOLO(str(gun_pt.resolve()))
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"Cannot open {video}")
    try:
        import torch

        det_device = 0 if torch.cuda.is_available() else "cpu"
    except ImportError:
        det_device = "cpu"
    fw = fh = 0
    frames = 0
    frames_with_person = 0
    frames_with_gun = 0
    gun_confs: list[float] = []
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        frames += 1
        if max_frames > 0 and frames > max_frames:
            break
        fh, fw = bgr.shape[:2]
        pres = person.predict(source=bgr, conf=person_conf, classes=[0], verbose=False, device=det_device)
        boxes = pres[0].boxes if pres else None
        if boxes is None or len(boxes) == 0:
            continue
        frames_with_person += 1
        xyxy = boxes.xyxy.cpu().numpy()
        any_gun_this_frame = False
        for row in xyxy:
            x1, y1, x2, y2 = _clamp_box(row, fw, fh)
            if (x2 - x1) < min_person_px or (y2 - y1) < min_person_px:
                continue
            qx1, qy1, qx2, qy2 = _expand_xyxy_frac(x1, y1, x2, y2, fw, fh, gun_roi_pad_frac)
            pr, pb = qx2 - qx1, qy2 - qy1
            if pr < min_person_px or pb < min_person_px:
                continue
            pcrop = bgr[qy1:qy2, qx1:qx2]
            if pcrop.size == 0:
                continue
            pch, pcw = pcrop.shape[:2]
            gres = gun.predict(
                source=pcrop,
                conf=take_best_infer_conf,
                imgsz=gun_imgsz,
                verbose=False,
                device=det_device,
            )
            gboxes = gres[0].boxes if gres else None
            gnames = dict(gres[0].names) if gres and hasattr(gres[0], "names") else {}
            picked = _pick_best_gun(
                gboxes,
                gnames,
                qx1,
                qy1,
                fw,
                fh,
                pcw,
                pch,
                pr,
                pb,
                take_best_infer_conf,
                max_area_frac,
                max_side_frac,
                gun_min_box_px,
            )
            if picked is not None:
                any_gun_this_frame = True
                gun_confs.append(picked[0])
        if any_gun_this_frame:
            frames_with_gun += 1
    cap.release()
    return {
        "video": str(video),
        "frames": frames,
        "frames_with_person": frames_with_person,
        "frames_with_valid_gun_box": frames_with_gun,
        "gun_rate_given_person_frame": (frames_with_gun / max(frames_with_person, 1)),
        "max_gun_conf": max(gun_confs) if gun_confs else 0.0,
        "mean_gun_conf_when_detected": float(np.mean(gun_confs)) if gun_confs else 0.0,
        "gun_passes_total": len(gun_confs),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--gun_pt", type=Path, required=True)
    p.add_argument("--person_yolo", type=str, default="yolov8n.pt")
    p.add_argument("--person_conf", type=float, default=0.25)
    p.add_argument("--min_person_px", type=int, default=24)
    p.add_argument("--gun_conf", type=float, default=0.25, help="Capped by gun_thermal like infer")
    p.add_argument("--gun_roi_pad_frac", type=float, default=0.06)
    p.add_argument("--gun_imgsz", type=int, default=800)
    p.add_argument("--max_area_frac", type=float, default=0.5)
    p.add_argument("--max_side_frac", type=float, default=0.88)
    p.add_argument("--gun_min_box_px", type=int, default=8)
    p.add_argument("--max_frames", type=int, default=0, help="0 = full video")
    args = p.parse_args()
    # Match infer --gun_thermal: gun_conf = min(user, 0.06); take-best infer conf = min(that, 0.01)
    gun_conf_thermal = min(args.gun_conf, 0.06)
    infer_gun = min(gun_conf_thermal, 0.01)
    stats = run_bench(
        args.video,
        args.gun_pt,
        person_conf=args.person_conf,
        min_person_px=args.min_person_px,
        gun_roi_pad_frac=args.gun_roi_pad_frac,
        gun_imgsz=args.gun_imgsz,
        max_area_frac=args.max_area_frac,
        max_side_frac=args.max_side_frac,
        gun_min_box_px=args.gun_min_box_px,
        take_best_infer_conf=infer_gun,
        max_frames=args.max_frames,
        person_yolo=args.person_yolo,
    )
    print()
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")
    print(f"  (infer gun conf threshold: {infer_gun})")


if __name__ == "__main__":
    main()
