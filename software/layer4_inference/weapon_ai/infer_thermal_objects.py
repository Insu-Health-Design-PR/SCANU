"""
Thermal stream: YOLO boxes (person-only by default) -> per-crop safe/unsafe score -> border on unsafe.

Non-person YOLO detections are not shown. Use --yolo_classes all to draw every COCO class again.

Optionally draws firearm boxes from a second YOLO detector (default: Subh775/Firearm_Detection_Yolov8n
on Hugging Face, AGPL-3.0). By default firearm YOLO runs only **inside each person box** (crop),
then boxes are mapped back to the full frame—reduces chair/background false positives. Use
--gun_full_frame to scan the whole image like before. Trained on visible-light imagery; on thermal it
often scores below normal conf thresholds and may predict huge, soft boxes—see --gun_thermal_debug
or lower --gun_conf and relax --gun_max_*_frac. Use --gun_thermal for a balanced thermal preset
(--gun_take_best + smaller gun_min_box_px). Fine-tuning on thermal gun crops is the durable fix.

Use a dedicated thermal extract, e.g. clip_thermal.mp4 from split_panels, or pass a composite
recording with --composite_mode and --thermal_panel.

For fresh-start training (`video_mode=gun_prob`), this script reads a BCE checkpoint and uses
sigmoid(logit) as p(gun). `--unsafe_threshold` (or `--gun_threshold`) decides border color.

  python -m weapon_ai.infer_thermal_objects --checkpoint trained_models/gun_detection/gun_prob_best.pt --source path/to_clip_thermal.mp4
  python -m weapon_ai.infer_thermal_objects --config weapon_ai/infer_thermal.example.yaml
  # CLI flags override values from the JSON/YAML file.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import torch
from torchvision import transforms
from ultralytics import YOLO

from .modeling import build_model

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_FIREARM_YOLO = _REPO_ROOT / "trained_models" / "gun_detection" / "firearm_yolov8n_best.pt"
_FIREARM_HF_URL = (
    "https://huggingface.co/Subh775/Firearm_Detection_Yolov8n/resolve/main/weights/best.pt"
)


def _ensure_firearm_yolo_weights(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return
    print(f"Downloading firearm YOLO weights (AGPL-3.0) -> {dest} ...")
    urllib.request.urlretrieve(_FIREARM_HF_URL, dest)  # noqa: S310 — fixed HF URL


def _firearm_box_plausible(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    fw: int,
    fh: int,
    max_area_frac: float,
    max_side_frac: float,
    *,
    ref_w: int | None = None,
    ref_h: int | None = None,
) -> bool:
    """Drop absurdly large false positives. If ref_w/ref_h set, limits are vs that ROI (e.g. person crop)."""
    if max_area_frac >= 1.0 and max_side_frac >= 1.0:
        return True
    bw, bh = x2 - x1, y2 - y1
    if bw <= 0 or bh <= 0:
        return False
    rw, rh = (fw, fh) if ref_w is None or ref_h is None else (ref_w, ref_h)
    area = bw * bh
    if max_area_frac < 1.0 and area > max_area_frac * rw * rh:
        return False
    if max_side_frac < 1.0 and (bw > max_side_frac * rw or bh > max_side_frac * rh):
        return False
    return True


def _clamp_box(xyxy: np.ndarray, w: int, h: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = xyxy.astype(int)
    x1 = max(0, min(x1, w - 1))
    x2 = max(0, min(x2, w))
    y1 = max(0, min(y1, h - 1))
    y2 = max(0, min(y2, h))
    if x2 <= x1:
        x2 = min(x1 + 1, w)
    if y2 <= y1:
        y2 = min(y1 + 1, h)
    return x1, y1, x2, y2


def _gun_detection_valid(
    gx1: int,
    gy1: int,
    gx2: int,
    gy2: int,
    fw: int,
    fh: int,
    max_area_frac: float,
    max_side_frac: float,
    gun_min_box_px: int,
    *,
    ref_w: int | None = None,
    ref_h: int | None = None,
) -> bool:
    if (gx2 - gx1) < gun_min_box_px or (gy2 - gy1) < gun_min_box_px:
        return False
    return _firearm_box_plausible(
        gx1,
        gy1,
        gx2,
        gy2,
        fw,
        fh,
        max_area_frac,
        max_side_frac,
        ref_w=ref_w,
        ref_h=ref_h,
    )


def _expand_xyxy_frac(
    x1: int, y1: int, x2: int, y2: int, fw: int, fh: int, pad_frac: float
) -> tuple[int, int, int, int]:
    """Pad a box by a fraction of its width/height (clamped to image)."""
    if pad_frac <= 0:
        return x1, y1, x2, y2
    bw, bh = x2 - x1, y2 - y1
    px = int(round(bw * pad_frac))
    py = int(round(bh * pad_frac))
    nx1 = max(0, x1 - px)
    ny1 = max(0, y1 - py)
    nx2 = min(fw, x2 + px)
    ny2 = min(fh, y2 + py)
    return nx1, ny1, nx2, ny2


def _expand_person_roi_for_gun(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    fw: int,
    fh: int,
    pad_frac: float,
    pad_px: int,
) -> tuple[int, int, int, int]:
    """Expand person box for firearm YOLO: fractional pad, then fixed pixels per side (clamped)."""
    qx1, qy1, qx2, qy2 = _expand_xyxy_frac(x1, y1, x2, y2, fw, fh, pad_frac)
    if pad_px <= 0:
        return qx1, qy1, qx2, qy2
    qx1 = max(0, qx1 - pad_px)
    qy1 = max(0, qy1 - pad_px)
    qx2 = min(fw, qx2 + pad_px)
    qy2 = min(fh, qy2 + pad_px)
    return qx1, qy1, qx2, qy2


def _extract_thermal_column(bgr: np.ndarray, panel: str) -> np.ndarray:
    h, w = bgr.shape[:2]
    if panel == "left":
        return bgr[:, : w // 3]
    if panel == "center":
        return bgr[:, w // 3 : 2 * w // 3]
    if panel == "right":
        return bgr[:, 2 * w // 3 :]
    raise ValueError(panel)


def _print_run_summary(
    source: str,
    all_probs: list[float],
    frame_count: int,
    frame_max_probs: list[float],
    unsafe_threshold: float,
    score_name: str,
) -> None:
    print()
    print("=" * 60)
    print(f"Run finished: {source}")
    print(f"Frames read: {frame_count}")
    if not all_probs:
        print(f"No person crops scored — cannot summarize {score_name}.")
        print("=" * 60)
        return
    arr = np.array(all_probs, dtype=np.float64)
    print(f"Person crops scored (total boxes): {len(all_probs)}")
    print(f"{score_name} over all crops — min: {arr.min():.4f}  mean: {arr.mean():.4f}  max: {arr.max():.4f}")
    if frame_max_probs:
        fm = np.array(frame_max_probs, dtype=np.float64)
        print(
            f"Per-frame max {score_name} — mean: {fm.mean():.4f}  peak (worst frame): {fm.max():.4f}"
        )
    peak = float(arr.max())
    verdict = "UNSAFE" if peak >= unsafe_threshold else "SAFE"
    print(
        f"FINAL (clip): {verdict}  |  peak {score_name}={peak:.4f}  (threshold={unsafe_threshold})"
    )
    print("=" * 60)


def _parse_yolo_classes(s: str | None) -> list[int] | None:
    if not s or not s.strip():
        return None
    t = s.strip().lower()
    if t == "all":
        return None
    return [int(x.strip()) for x in s.split(",") if x.strip()]


# Keys accepted inside --config (flat dict); unknown keys are ignored with a warning.
_INFER_CONFIG_KEYS = frozenset(
    {
        "checkpoint",
        "source",
        "image_size",
        "yolo_model",
        "conf",
        "min_box_px",
        "yolo_classes",
        "unsafe_threshold",
        "unsafe_border_thick",
        "unsafe_border_color",
        "composite_mode",
        "thermal_panel",
        "show_yolo_name",
        "output",
        "no_imshow",
        "max_frames",
        "gun_yolo_model",
        "no_gun_yolo",
        "gun_conf",
        "gun_max_area_frac",
        "gun_max_side_frac",
        "gun_full_frame",
        "gun_roi_pad_frac",
        "gun_roi_pad_px",
        "gun_imgsz",
        "gun_thermal_debug",
        "gun_thermal",
        "gun_min_box_px",
        "gun_take_best",
        "gun_threshold",
        "fuse_gun_to_prob",
        "gun_prob_floor",
        "gun_conf_scale",
        "live_jpg",
    }
)


def _load_infer_config(path: Path) -> dict:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"Config file not found: {path}")
    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8")
    if suffix == ".json":
        data = json.loads(raw)
    elif suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as e:
            raise SystemExit(
                "YAML config requires PyYAML. Install with: pip install PyYAML"
            ) from e
        data = yaml.safe_load(raw)
    else:
        raise SystemExit(f"Unsupported config format (use .json, .yaml, .yml): {path}")
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SystemExit(f"Config root must be a JSON/YAML object, got {type(data).__name__}")
    return data


def _coerce_infer_config_values(cfg: dict) -> dict:
    """Normalize types from JSON/YAML for argparse/set_defaults."""
    out = dict(cfg)
    if "checkpoint" in out and out["checkpoint"] is not None:
        out["checkpoint"] = Path(out["checkpoint"])
    if "output" in out and out["output"] is not None and out["output"] != "":
        out["output"] = Path(out["output"])
    if "gun_yolo_model" in out and out["gun_yolo_model"] is not None:
        out["gun_yolo_model"] = Path(out["gun_yolo_model"])
    if "live_jpg" in out and out["live_jpg"] is not None and out["live_jpg"] != "":
        out["live_jpg"] = Path(out["live_jpg"])
    if "source" in out and out["source"] is not None and not isinstance(out["source"], str):
        out["source"] = str(out["source"])
    return out


def _filter_infer_config(cfg: dict, path: Path) -> dict:
    extra = set(cfg) - _INFER_CONFIG_KEYS
    if extra:
        print(f"Warning: ignoring unknown config keys in {path}: {sorted(extra)}", file=sys.stderr)
    return {k: v for k, v in cfg.items() if k in _INFER_CONFIG_KEYS}


def main() -> None:
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument(
        "--config",
        type=Path,
        default=None,
        help="JSON or YAML file with infer options; CLI overrides file.",
    )
    pre_args, argv_rest = pre.parse_known_args()
    file_defaults: dict = {}
    if pre_args.config is not None:
        loaded = _load_infer_config(pre_args.config)
        file_defaults = _coerce_infer_config_values(_filter_infer_config(loaded, pre_args.config))

    p = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Use --config path.yaml or path.json (before other flags) to load options; "
            "CLI arguments override the file. See weapon_ai/infer_thermal.example.yaml."
        ),
    )
    p.add_argument("--checkpoint", type=Path, default=None)
    p.add_argument("--source", type=str, default=None, help="thermal .mp4 path or webcam index")
    p.add_argument("--image_size", type=int, default=224)
    p.add_argument("--yolo_model", type=str, default="yolov8n.pt")
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--min_box_px", type=int, default=24)
    p.add_argument(
        "--yolo_classes",
        type=str,
        default="0",
        help='COCO class ids to keep, comma-separated. Default "0" = person only (no box for other objects). '
        'Use "all" to run every YOLO class.',
    )
    p.add_argument(
        "--unsafe_threshold",
        type=float,
        default=0.5,
        help="Threat score threshold at or above this draws the unsafe border.",
    )
    p.add_argument(
        "--gun_threshold",
        type=float,
        default=None,
        help="Alias for --unsafe_threshold when using a gun-probability checkpoint.",
    )
    p.add_argument(
        "--fuse_gun_to_prob",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="If a firearm box is detected in the frame, boost person p(gun) using gun confidence.",
    )
    p.add_argument(
        "--gun_prob_floor",
        type=float,
        default=0.60,
        help="Minimum fused p(gun) when firearm YOLO detects a valid box in the frame.",
    )
    p.add_argument(
        "--gun_conf_scale",
        type=float,
        default=2.0,
        help="Scale factor for firearm confidence when fusing into p(gun).",
    )
    p.add_argument(
        "--unsafe_border_thick",
        type=int,
        default=4,
        help="Border thickness in pixels for UNSAFE boxes.",
    )
    p.add_argument(
        "--unsafe_border_color",
        type=str,
        default="red",
        choices=["red", "black", "white", "yellow"],
        help="Border color for UNSAFE boxes (BGR via named preset).",
    )
    p.add_argument(
        "--composite_mode",
        action="store_true",
        help="Source is 3-panel composite; thermal is taken from --thermal_panel strip only.",
    )
    p.add_argument(
        "--thermal_panel",
        choices=["left", "center", "right"],
        default="left",
        help="Which third of composite is thermal (when --composite_mode).",
    )
    p.add_argument(
        "--show_yolo_name",
        action="store_true",
        help="Prefix label with YOLO class name (e.g. person).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write annotated preview to this video file (e.g. preview.mp4). Same overlays as the live window.",
    )
    p.add_argument(
        "--live_jpg",
        type=Path,
        default=None,
        help="Each processed frame, atomically write this JPEG path (for Layer 8 MJPEG preview).",
    )
    p.add_argument(
        "--no_imshow",
        action="store_true",
        help="Do not open cv2.imshow (batch / headless). Use with --output.",
    )
    p.add_argument(
        "--max_frames",
        type=int,
        default=0,
        help="Stop after this many frames (0 = entire clip).",
    )
    p.add_argument(
        "--gun_yolo_model",
        type=Path,
        default=None,
        help=f"Firearm-detection YOLO .pt (Ultralytics). Default: {_DEFAULT_FIREARM_YOLO} (auto-download if missing).",
    )
    p.add_argument(
        "--no_gun_yolo",
        action="store_true",
        help="Disable second-stage firearm boxes.",
    )
    p.add_argument(
        "--gun_conf",
        type=float,
        default=0.25,
        help="With --gun-take-best (default): Ultralytics conf=min(this, 0.01). With --no-gun-take-best: conf is this value only.",
    )
    p.add_argument(
        "--gun_min_box_px",
        type=int,
        default=8,
        help="Min width/height (px) for an orange firearm box; person --min_box_px does not apply to guns.",
    )
    p.add_argument(
        "--gun_take_best",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Infer firearm YOLO at low conf and draw one best plausible box per person (default: on).",
    )
    p.add_argument(
        "--gun_thermal",
        action="store_true",
        help="Preset for RGB firearm weights on thermal: take-best, lower gun_conf, relaxed size limits, imgsz≥800, ROI pad.",
    )
    p.add_argument(
        "--gun_max_area_frac",
        type=float,
        default=0.22,
        help="Skip firearm boxes if area exceeds this fraction of the frame (thermal false positives are often huge). Set to 1.0 to disable.",
    )
    p.add_argument(
        "--gun_max_side_frac",
        type=float,
        default=0.65,
        help="Skip firearm boxes if width or height exceeds this fraction of frame W/H. Set to 1.0 to disable.",
    )
    p.add_argument(
        "--gun_full_frame",
        action="store_true",
        help="Run firearm YOLO on the full thermal frame (legacy). Default: only inside each person box crop.",
    )
    p.add_argument(
        "--gun_roi_pad_frac",
        type=float,
        default=0.0,
        help="Expand each person box by this fraction of its width/height before firearm YOLO (clamped to frame).",
    )
    p.add_argument(
        "--gun_roi_pad_px",
        type=int,
        default=0,
        help="After fractional pad, expand the person ROI by this many pixels on each side (clamped to frame).",
    )
    p.add_argument(
        "--gun_imgsz",
        type=int,
        default=640,
        help="Inference image size for firearm YOLO (larger can help tiny regions; slower).",
    )
    p.add_argument(
        "--gun_thermal_debug",
        action="store_true",
        help="RGB firearm model on thermal: set conf=0.02 and disable size filters (1.0). Expect large, imprecise boxes; use for demos only.",
    )
    if file_defaults:
        p.set_defaults(**file_defaults)
    args = p.parse_args(argv_rest)

    if pre_args.config is not None:
        print(f"Loaded infer config: {pre_args.config.resolve()}")

    if args.checkpoint is None:
        raise SystemExit(
            "Missing --checkpoint. Add it to your config file or pass it on the command line."
        )
    if args.source is None:
        raise SystemExit(
            "Missing --source. Add it to your config file or pass it on the command line."
        )
    if args.gun_threshold is not None:
        args.unsafe_threshold = float(args.gun_threshold)

    if args.gun_thermal_debug:
        args.gun_conf = 0.02
        args.gun_max_area_frac = 1.0
        args.gun_max_side_frac = 1.0
    elif args.gun_thermal:
        args.gun_take_best = True
        args.gun_conf = min(args.gun_conf, 0.06)
        args.gun_max_area_frac = 0.5
        args.gun_max_side_frac = 0.88
        args.gun_imgsz = max(args.gun_imgsz, 800)
        args.gun_roi_pad_frac = max(args.gun_roi_pad_frac, 0.06)

    _unsafe_bgr = {
        "red": (0, 0, 255),
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "yellow": (0, 255, 255),
    }[args.unsafe_border_color]
    _unsafe_text_bgr = (0, 0, 255) if args.unsafe_border_color == "black" else _unsafe_bgr

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ck = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    arch = ck.get("arch", "mobilenet_v3_small")
    is_gun_prob = (
        ck.get("objective") == "gun_prob_bce"
        or ck.get("video_mode") == "gun_prob"
        or int(ck.get("num_classes", 2)) == 1
    )
    score_name = "p(gun)" if is_gun_prob else "p(unsafe)"
    clf = build_model(arch, num_classes=1 if is_gun_prob else 2).to(device)
    clf.load_state_dict(ck["model"])
    clf.eval()
    infer_gray3 = str(ck.get("preprocess", "")).startswith("gray3ch")

    tf = transforms.Compose(
        [
            transforms.ToPILImage(),
            transforms.Resize((args.image_size, args.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )

    yolo_classes = _parse_yolo_classes(args.yolo_classes)
    person_only = yolo_classes is not None and yolo_classes == [0]
    detector = YOLO(args.yolo_model)
    det_device = 0 if device.type == "cuda" else "cpu"

    gun_detector: YOLO | None = None
    if not args.no_gun_yolo:
        gpath = args.gun_yolo_model if args.gun_yolo_model is not None else _DEFAULT_FIREARM_YOLO
        gpath = Path(gpath).resolve()
        _ensure_firearm_yolo_weights(gpath)
        gun_detector = YOLO(str(gpath))

    src = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open {args.source}")

    det_mode = "person only" if person_only else ("all YOLO classes" if yolo_classes is None else str(yolo_classes))
    print(
        f"q=quit | YOLO ({det_mode}) on thermal | label = safe/UNSAFE + {score_name} | "
        "UNSAFE = colored border (not filled)"
    )
    if gun_detector is not None:
        roi = "full frame" if args.gun_full_frame else "inside each person box only"
        print(
            f"Firearm YOLO: orange boxes (AGPL-3.0) — search: {roi}. "
            f"Size filter vs ROI/frame: area≤{args.gun_max_area_frac:.0%}, side≤{args.gun_max_side_frac:.0%}."
        )
        print(f"Firearm YOLO imgsz={args.gun_imgsz}.")
        if args.gun_thermal_debug:
            print(
                "WARNING: --gun_thermal_debug — low conf, size filters off; boxes are often wrong on thermal."
            )
        if args.gun_roi_pad_frac > 0:
            print(f"Person ROI pad for firearm pass: {args.gun_roi_pad_frac:.0%} of box size.")
        if int(args.gun_roi_pad_px) > 0:
            print(f"Person ROI extra pad for firearm pass: {int(args.gun_roi_pad_px)} px per side.")
        if args.gun_thermal:
            print("Preset --gun_thermal: take-best firearm box, relaxed size limits, larger imgsz.")
        if args.gun_take_best:
            print(
                "Firearm YOLO take-best: infer conf=min(your --gun_conf, 0.01); draw one best valid box per person."
            )
    if args.output is not None:
        args.output = args.output.resolve()
        args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.live_jpg is not None:
        args.live_jpg = args.live_jpg.expanduser().resolve()
        args.live_jpg.parent.mkdir(parents=True, exist_ok=True)
    print("Summary prints when the video ends or you press q.")
    all_probs: list[float] = []
    frame_max_probs: list[float] = []
    frame_count = 0
    writer: cv2.VideoWriter | None = None
    try:
        with torch.no_grad():
            while True:
                ok, bgr_full = cap.read()
                if not ok:
                    break
                frame_count += 1
                if args.max_frames and frame_count > args.max_frames:
                    break

                if args.composite_mode:
                    thermal = _extract_thermal_column(bgr_full, args.thermal_panel)
                else:
                    thermal = bgr_full

                vis = thermal.copy()
                h, w = vis.shape[:2]

                pred_kw: dict = dict(
                    source=thermal,
                    conf=args.conf,
                    verbose=False,
                    device=det_device,
                )
                if yolo_classes is not None:
                    pred_kw["classes"] = yolo_classes

                results = detector.predict(**pred_kw)
                boxes = results[0].boxes if results else None
                id_to_name = results[0].names if results and hasattr(results[0], "names") else {}

                rows: list[
                    tuple[int, int, int, int, float, int | None, str]
                ] = []  # x1,y1,x2,y2, threat_score, cls_id, yolo_tag

                if boxes is not None and len(boxes) > 0:
                    xyxy = boxes.xyxy.cpu().numpy()
                    cls_ids = boxes.cls.cpu().numpy().astype(int) if boxes.cls is not None else None
                    for i, row in enumerate(xyxy):
                        x1, y1, x2, y2 = _clamp_box(row, w, h)
                        if (x2 - x1) < args.min_box_px or (y2 - y1) < args.min_box_px:
                            continue
                        crop_bgr = thermal[y1:y2, x1:x2]
                        if crop_bgr.size == 0:
                            continue
                        if crop_bgr.ndim == 2:
                            crop_bgr = cv2.cvtColor(crop_bgr, cv2.COLOR_GRAY2BGR)
                        if infer_gray3:
                            gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
                            in_rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
                        else:
                            in_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
                        x = tf(in_rgb).unsqueeze(0).to(device)
                        logits = clf(x)
                        if is_gun_prob:
                            prob = torch.sigmoid(logits.reshape(-1))[0].item()
                        else:
                            prob = torch.softmax(logits, dim=1)[0, 1].item()
                        cid = int(cls_ids[i]) if cls_ids is not None and i < len(cls_ids) else None
                        yolo_tag = id_to_name.get(cid, str(cid)) if cid is not None else "obj"
                        rows.append((x1, y1, x2, y2, prob, cid, yolo_tag))

                gun_count = 0
                frame_gun_best_conf = 0.0
                if gun_detector is not None:
                    if args.gun_thermal_debug:
                        infer_gun_conf = float(args.gun_conf)
                    elif args.gun_take_best:
                        infer_gun_conf = min(float(args.gun_conf), 0.01)
                    else:
                        infer_gun_conf = float(args.gun_conf)

                    gnames: dict = {}

                    def _emit_firearm_overlay(gx1: int, gy1: int, gx2: int, gy2: int, gname: str, gc: float) -> None:
                        nonlocal gun_count, frame_gun_best_conf
                        gx1, gy1, gx2, gy2 = max(0, gx1), max(0, gy1), min(w, gx2), min(h, gy2)
                        gun_count += 1
                        frame_gun_best_conf = max(frame_gun_best_conf, float(gc))
                        glabel = f"{gname} {gc:.2f}"
                        orange = (0, 140, 255)
                        cv2.rectangle(vis, (gx1, gy1), (gx2, gy2), orange, 3)
                        gty = max(gy1 - 6, 18)
                        cv2.putText(
                            vis,
                            glabel,
                            (gx1, gty),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            orange,
                            2,
                        )

                    def _draw_gun_from_candidates(
                        candidates: list[tuple[float, int, int, int, int, str]],
                        pr: int,
                        pb: int,
                    ) -> None:
                        if not candidates:
                            return
                        normed: list[tuple[float, int, int, int, int, str]] = []
                        for gc, gx1, gy1, gx2, gy2, gnm in candidates:
                            gx1, gy1, gx2, gy2 = max(0, gx1), max(0, gy1), min(w, gx2), min(h, gy2)
                            normed.append((gc, gx1, gy1, gx2, gy2, gnm))
                        if args.gun_take_best:
                            for gc, gx1, gy1, gx2, gy2, gnm in sorted(normed, key=lambda t: -t[0]):
                                if _gun_detection_valid(
                                    gx1,
                                    gy1,
                                    gx2,
                                    gy2,
                                    w,
                                    h,
                                    args.gun_max_area_frac,
                                    args.gun_max_side_frac,
                                    args.gun_min_box_px,
                                    ref_w=pr,
                                    ref_h=pb,
                                ):
                                    _emit_firearm_overlay(gx1, gy1, gx2, gy2, gnm, gc)
                                    return
                            return
                        for gc, gx1, gy1, gx2, gy2, gnm in normed:
                            if not _gun_detection_valid(
                                gx1,
                                gy1,
                                gx2,
                                gy2,
                                w,
                                h,
                                args.gun_max_area_frac,
                                args.gun_max_side_frac,
                                args.gun_min_box_px,
                                ref_w=pr,
                                ref_h=pb,
                            ):
                                continue
                            _emit_firearm_overlay(gx1, gy1, gx2, gy2, gnm, gc)

                    if args.gun_full_frame:
                        gres = gun_detector.predict(
                            source=thermal,
                            conf=infer_gun_conf,
                            imgsz=args.gun_imgsz,
                            verbose=False,
                            device=det_device,
                        )
                        gboxes = gres[0].boxes if gres else None
                        gnames = dict(gres[0].names) if gres and hasattr(gres[0], "names") else {}
                        candidates_ff: list[tuple[float, int, int, int, int, str]] = []
                        if gboxes is not None and len(gboxes) > 0:
                            g_xyxy = gboxes.xyxy.cpu().numpy()
                            g_cls = gboxes.cls.cpu().numpy().astype(int) if gboxes.cls is not None else None
                            g_conf = gboxes.conf.cpu().numpy() if gboxes.conf is not None else None
                            for j, grow in enumerate(g_xyxy):
                                gx1, gy1, gx2, gy2 = _clamp_box(grow, w, h)
                                cid = int(g_cls[j]) if g_cls is not None and j < len(g_cls) else 0
                                gnm = gnames.get(cid, "gun")
                                gc = float(g_conf[j]) if g_conf is not None and j < len(g_conf) else 0.0
                                candidates_ff.append((gc, gx1, gy1, gx2, gy2, gnm))
                        _draw_gun_from_candidates(candidates_ff, w, h)
                    elif rows:
                        for px1, py1, px2, py2, _prob, pcid, ptag in rows:
                            if pcid is not None and pcid != 0:
                                continue
                            qx1, qy1, qx2, qy2 = _expand_person_roi_for_gun(
                                px1,
                                py1,
                                px2,
                                py2,
                                w,
                                h,
                                args.gun_roi_pad_frac,
                                int(args.gun_roi_pad_px),
                            )
                            pr, pb = qx2 - qx1, qy2 - qy1
                            if pr < args.min_box_px or pb < args.min_box_px:
                                continue
                            pcrop = thermal[qy1:qy2, qx1:qx2]
                            if pcrop.size == 0:
                                continue
                            gres = gun_detector.predict(
                                source=pcrop,
                                conf=infer_gun_conf,
                                imgsz=args.gun_imgsz,
                                verbose=False,
                                device=det_device,
                            )
                            if gres and hasattr(gres[0], "names"):
                                gnames = dict(gres[0].names)
                            gboxes = gres[0].boxes if gres else None
                            candidates_roi: list[tuple[float, int, int, int, int, str]] = []
                            if gboxes is not None and len(gboxes) > 0:
                                g_xyxy = gboxes.xyxy.cpu().numpy()
                                g_cls = gboxes.cls.cpu().numpy().astype(int) if gboxes.cls is not None else None
                                g_conf = gboxes.conf.cpu().numpy() if gboxes.conf is not None else None
                                cw, ch = pcrop.shape[1], pcrop.shape[0]
                                for j, grow in enumerate(g_xyxy):
                                    lx1, ly1, lx2, ly2 = _clamp_box(grow, cw, ch)
                                    gx1, gy1 = qx1 + lx1, qy1 + ly1
                                    gx2, gy2 = qx1 + lx2, qy1 + ly2
                                    cid = int(g_cls[j]) if g_cls is not None and j < len(g_cls) else 0
                                    gnm = gnames.get(cid, "gun")
                                    gc = float(g_conf[j]) if g_conf is not None and j < len(g_conf) else 0.0
                                    candidates_roi.append((gc, gx1, gy1, gx2, gy2, gnm))
                            _draw_gun_from_candidates(candidates_roi, pr, pb)

                if args.fuse_gun_to_prob and gun_count > 0 and rows:
                    gun_boost = max(
                        float(args.gun_prob_floor),
                        min(0.99, float(frame_gun_best_conf) * float(args.gun_conf_scale)),
                    )
                    rows = [
                        (x1, y1, x2, y2, max(prob, gun_boost), cid, ytag)
                        for (x1, y1, x2, y2, prob, cid, ytag) in rows
                    ]

                if rows:
                    probs = [r[4] for r in rows]
                    all_probs.extend(probs)
                    frame_max_probs.append(max(probs))

                unsafe_first: list[tuple[int, int, int, int, float, str]] = []
                safe_list: list[tuple[int, int, int, int, float, str]] = []
                for x1, y1, x2, y2, prob, _cid, ytag in rows:
                    prefix = f"{ytag} " if args.show_yolo_name else ""
                    label_txt = f"{prefix}{'UNSAFE' if prob >= args.unsafe_threshold else 'safe'} {prob:.2f}"
                    if prob >= args.unsafe_threshold:
                        unsafe_first.append((x1, y1, x2, y2, prob, label_txt))
                    else:
                        safe_list.append((x1, y1, x2, y2, prob, label_txt))

                for x1, y1, x2, y2, _prob, label_txt in safe_list:
                    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 220, 0), 2)
                    ty = max(y1 - 6, 18)
                    cv2.putText(
                        vis,
                        label_txt,
                        (x1, ty),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 220, 0),
                        2,
                    )

                for x1, y1, x2, y2, _prob, label_txt in unsafe_first:
                    cv2.rectangle(
                        vis,
                        (x1, y1),
                        (x2, y2),
                        _unsafe_bgr,
                        thickness=max(1, args.unsafe_border_thick),
                    )
                    ty = max(y1 - 6, 18)
                    cv2.putText(
                        vis,
                        label_txt,
                        (x1, ty),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        _unsafe_text_bgr,
                        2,
                    )

                if not rows:
                    if gun_count > 0:
                        msg = "no person | firearm box(es) shown"
                    else:
                        msg = "no person detected" if person_only else "no objects (YOLO)"
                    cv2.putText(
                        vis,
                        msg,
                        (10, 26),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (180, 180, 180),
                        2,
                    )

                if args.output is not None:
                    if writer is None:
                        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
                        if fps < 1.0:
                            fps = 30.0
                        hh, ww = vis.shape[:2]
                        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                        writer = cv2.VideoWriter(str(args.output), fourcc, fps, (ww, hh))
                        if not writer.isOpened():
                            raise SystemExit(f"Cannot open VideoWriter for {args.output}")
                    writer.write(vis)

                if args.live_jpg is not None:
                    tmp = args.live_jpg.with_suffix(args.live_jpg.suffix + ".tmp")
                    ok_lj, buf = cv2.imencode(".jpg", vis, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                    if ok_lj:
                        tmp.write_bytes(buf.tobytes())
                        tmp.replace(args.live_jpg)

                if not args.no_imshow:
                    title = "thermal | objects + threat (border = unsafe)"
                    cv2.imshow(title, vis)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
    finally:
        if writer is not None:
            writer.release()
        cap.release()
        cv2.destroyAllWindows()
        _print_run_summary(
            str(src),
            all_probs,
            frame_count,
            frame_max_probs,
            args.unsafe_threshold,
            score_name,
        )


if __name__ == "__main__":
    main()
