#!/usr/bin/env python3
"""
Offline Layer 4 test: run thermal object-detection + same box drawing as Layer 8
on one or more videos (e.g. under ~/Desktop/weapon_test_data).

Usage (from repo software/ directory — required so ``layer4_inference`` imports):

  cd ~/Desktop/SCANU/software

  python3 -m layer4_inference.examples.run_layer4_video_boxes \\
    --input /home/insu/Desktop/weapon_test_data/weapon_screening_v2_person_x264.mp4

If you see "PyTorch >= 2.4" / torch 1.8: use software/layer4_inference/requirements.txt
(``pip install --user --force-reinstall 'transformers>=4.43,<5'``) or install NVIDIA Jetson PyTorch.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_software = Path(__file__).resolve().parents[2]
if str(_software) not in sys.path:
    sys.path.insert(0, str(_software))

import cv2  # noqa: E402

from layer4_inference import (  # noqa: E402
    InferenceEngine,
    ThermalThreatDetector,
    draw_detections_on_image,
)
from layer4_inference.thermal_detector import ml_stack_error_hint  # noqa: E402


def _preflight_ml_stack() -> str | None:
    """Return an error message if torch/transformers are unusable; else None."""
    try:
        import torch

        tver = str(getattr(torch, "__version__", ""))
    except Exception as exc:
        return ml_stack_error_hint(cause=exc)

    try:
        import transformers

        fver = str(getattr(transformers, "__version__", ""))
    except Exception as exc:
        return ml_stack_error_hint(cause=exc)

    def _major_minor(ver: str) -> tuple[int, int]:
        ver = ver.split("+", 1)[0].strip()
        parts = ver.split(".")
        try:
            return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        except ValueError:
            return 0, 0

    tmaj, tmin = _major_minor(tver)
    fmaj_str = fver.split(".")[0] if fver else "0"
    fmaj = int(fmaj_str) if fmaj_str.isdigit() else 0
    if fmaj >= 5 and (tmaj < 2 or (tmaj == 2 and tmin < 4)):
        return (
            f"Incompatible stack: transformers {fver!r} expects PyTorch >= 2.4, "
            f"but torch is {tver!r} (common: Jetson/Ubuntu apt torch 1.8). "
            "Fix: pip install --user --force-reinstall 'transformers>=4.43,<5' "
            "OR install NVIDIA Jetson PyTorch for your JetPack. "
            "Details: software/layer4_inference/requirements.txt"
        )
    return None


def _collect_inputs(root: Path, pattern: str, recursive: bool) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        return []
    if recursive:
        return sorted(root.rglob(pattern))
    return sorted(root.glob(pattern))


def _ensure_bgr(frame):
    if frame is None:
        return None
    if frame.ndim == 2:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    if frame.ndim == 3 and frame.shape[2] == 4:
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    return frame


def process_one_video(
    *,
    video_path: Path,
    out_path: Path,
    threshold: float,
    model_id: str | None,
    device: int,
    every_n: int,
    max_frames: int | None,
) -> dict:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if w <= 0 or h <= 0:
        cap.release()
        raise RuntimeError(f"Bad frame size for {video_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, float(fps), (w, h))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Cannot open VideoWriter for {out_path}")

    det = ThermalThreatDetector(model_id=model_id or None, threshold=threshold, device=device)
    engine = InferenceEngine(detector=det)

    frame_i = 0
    written = 0
    total_dets = 0
    frames_with_dets = 0
    last_dets: list = []
    t0 = time.perf_counter()

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            frame_i += 1
            if max_frames is not None and frame_i > max_frames:
                break

            bgr = _ensure_bgr(frame)
            out = bgr.copy()

            if every_n <= 1 or frame_i % every_n == 0:
                res = engine.infer(frame_i, time.time() * 1000.0, bgr)
                last_dets = list(res.detections)
                if last_dets:
                    frames_with_dets += 1
                    total_dets += len(last_dets)

            if last_dets:
                draw_detections_on_image(
                    out,
                    last_dets,
                    box_source_width=w,
                    box_source_height=h,
                )

            writer.write(out)
            written += 1
    finally:
        cap.release()
        writer.release()

    elapsed = time.perf_counter() - t0
    return {
        "input": str(video_path),
        "output": str(out_path),
        "frames_read": frame_i,
        "frames_written": written,
        "frames_with_detections": frames_with_dets,
        "detection_instances": total_dets,
        "seconds": round(elapsed, 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Layer 4 boxes on video (offline test).")
    ap.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Video file or directory of videos",
    )
    ap.add_argument(
        "--glob",
        dest="glob_pat",
        default="*.mp4",
        help="When input is a directory, glob pattern (default: *.mp4)",
    )
    ap.add_argument(
        "--no-recursive",
        action="store_true",
        help="When input is a directory, do not recurse into subfolders",
    )
    _default_out = Path(__file__).resolve().parent / "_video_out"
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=_default_out,
        help="Directory for annotated MP4s",
    )
    ap.add_argument("--threshold", type=float, default=0.25)
    ap.add_argument("--model-id", type=str, default="", help="Hugging Face model id (empty = default)")
    ap.add_argument("--device", type=int, default=-1, help="transformers device (-1 CPU)")
    ap.add_argument(
        "--every-n",
        type=int,
        default=1,
        help="Run detector every N frames (reuse previous boxes between runs)",
    )
    ap.add_argument("--max-frames", type=int, default=0, help="Stop after this many frames (0 = all)")
    ap.add_argument("--max-files", type=int, default=0, help="Process at most N files when input is dir (0 = all)")
    args = ap.parse_args()

    pre = _preflight_ml_stack()
    if pre:
        print(pre, file=sys.stderr, flush=True)
        return 3

    paths = _collect_inputs(args.input.resolve(), args.glob_pat, recursive=not args.no_recursive)
    if args.max_files and args.max_files > 0:
        paths = paths[: args.max_files]
    if not paths:
        print(f"No files matched: {args.input} pattern={args.glob_pat!r}", file=sys.stderr)
        return 2

    max_frames = args.max_frames if args.max_frames > 0 else None
    model_id = args.model_id.strip() or None
    summaries: list[dict] = []

    for vp in paths:
        rel = vp.name
        out_path = (args.output_dir.resolve() / rel).with_name(vp.stem + "_layer4_boxes.mp4")
        print(f"Processing {vp} -> {out_path}", flush=True)
        try:
            s = process_one_video(
                video_path=vp,
                out_path=out_path,
                threshold=float(args.threshold),
                model_id=model_id,
                device=int(args.device),
                every_n=max(1, int(args.every_n)),
                max_frames=max_frames,
            )
            summaries.append(s)
            print(
                f"  frames={s['frames_written']} with_dets={s['frames_with_detections']} "
                f"dets={s['detection_instances']} time={s['seconds']}s",
                flush=True,
            )
        except Exception as exc:
            print(f"  FAILED: {exc}", file=sys.stderr, flush=True)
            summaries.append({"input": str(vp), "error": str(exc)})

    ok = sum(1 for s in summaries if "error" not in s)
    print(f"\nDone: {ok}/{len(summaries)} ok")
    return 0 if ok == len(summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
