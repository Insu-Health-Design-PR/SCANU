"""
Convert RGB video or stills to a pseudo-thermal look (grayscale + CLAHE + colormap).

Full clip (recommended for bench / training parity with real thermal length):

  python -m scripts.weapon_tools.rgb_to_pseudo_thermal --mode video --input-dir data/collecting_data/dual_camera --pattern "*_rgb.mp4"

Single snapshot -> short MP4 (repeated frame, for quick tests only):

  python -m scripts.weapon_tools.rgb_to_pseudo_thermal --mode snapshot --pattern "*_rgb_snapshot.png"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def bgr_to_pseudo_thermal(
    bgr: np.ndarray,
    *,
    clip_limit: float = 2.0,
    tile: int = 8,
    colormap: int = cv2.COLORMAP_INFERNO,
) -> np.ndarray:
    if bgr.ndim == 2:
        gray = bgr
    else:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile, tile))
    eq = clahe.apply(gray)
    return cv2.applyColorMap(eq, colormap)


def _open_writer(
    path: Path,
    fps: float,
    frame_size: tuple[int, int],
    codec_preference: tuple[str, ...] = ("mp4v", "avc1"),
) -> cv2.VideoWriter:
    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = frame_size
    for codec in codec_preference:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
        if writer.isOpened():
            return writer
        writer.release()
    raise RuntimeError(f"Could not open VideoWriter for {path}")


def rgb_video_to_pseudo_thermal_mp4(
    src_mp4: Path,
    out_path: Path,
    *,
    codec_preference: tuple[str, ...] = ("mp4v", "avc1"),
) -> None:
    cap = cv2.VideoCapture(str(src_mp4))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {src_mp4}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps < 1e-3:
        fps = 30.0

    ok, first = cap.read()
    if not ok or first is None:
        cap.release()
        raise RuntimeError(f"No frames in {src_mp4}")

    h, w = first.shape[:2]
    writer = _open_writer(out_path, fps, (w, h), codec_preference)
    try:
        f = bgr_to_pseudo_thermal(first)
        writer.write(f)
        while True:
            ok, bgr = cap.read()
            if not ok or bgr is None:
                break
            writer.write(bgr_to_pseudo_thermal(bgr))
    finally:
        writer.release()
        cap.release()


def snapshot_png_to_mp4(
    png_path: Path,
    out_path: Path,
    *,
    seconds: float = 1.0,
    fps: float = 30.0,
    codec_preference: tuple[str, ...] = ("mp4v", "avc1"),
) -> None:
    bgr = cv2.imread(str(png_path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"Cannot read image: {png_path}")
    pseudo = bgr_to_pseudo_thermal(bgr)
    h, w = pseudo.shape[:2]
    n_frames = max(1, int(round(seconds * fps)))
    writer = _open_writer(out_path, fps, (w, h), codec_preference)
    try:
        for _ in range(n_frames):
            writer.write(pseudo)
    finally:
        writer.release()


def output_path_for_rgb_video(mp4: Path) -> Path:
    stem = mp4.stem
    if stem.endswith("_rgb"):
        base = stem[: -len("_rgb")]
    else:
        base = stem
    return mp4.parent / f"{base}_pseudo_thermal.mp4"


def output_path_for_rgb_snapshot(png: Path) -> Path:
    stem = png.stem
    if stem.endswith("_rgb_snapshot"):
        base = stem[: -len("_rgb_snapshot")]
    else:
        base = stem
    return png.parent / f"{base}_pseudo_thermal.mp4"


def main() -> None:
    p = argparse.ArgumentParser(description="RGB -> pseudo-thermal MP4 (full video or snapshot teaser)")
    p.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/collecting_data/dual_camera"),
        help="Directory containing inputs",
    )
    p.add_argument(
        "--mode",
        choices=("video", "snapshot"),
        default="video",
        help="video: every frame from *_rgb.mp4. snapshot: still -> short repeated-frame MP4.",
    )
    p.add_argument(
        "--pattern",
        type=str,
        default="",
        help="Glob under input-dir. Default: *_rgb.mp4 (video) or *_rgb_snapshot.png (snapshot).",
    )
    p.add_argument("--seconds", type=float, default=1.0, help="Snapshot mode only: MP4 length")
    p.add_argument("--fps", type=float, default=30.0, help="Snapshot mode only: nominal fps")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    root = args.input_dir.resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")

    pattern = args.pattern.strip() or (
        "*_rgb.mp4" if args.mode == "video" else "*_rgb_snapshot.png"
    )
    paths = sorted(root.glob(pattern))
    if not paths:
        print(f"No files matched {root} / {pattern}")
        return

    for src in paths:
        if args.mode == "video":
            if src.suffix.lower() != ".mp4":
                print(f"Skip (not .mp4): {src.name}")
                continue
            out = output_path_for_rgb_video(src)
            print(f"{src.name} -> {out.name} (full video)")
            if args.dry_run:
                continue
            rgb_video_to_pseudo_thermal_mp4(src, out)
        else:
            if src.suffix.lower() not in (".png", ".jpg", ".jpeg"):
                print(f"Skip (not image): {src.name}")
                continue
            out = output_path_for_rgb_snapshot(src)
            print(f"{src.name} -> {out.name} (snapshot teaser)")
            if args.dry_run:
                continue
            snapshot_png_to_mp4(src, out, seconds=args.seconds, fps=args.fps)

    print(f"Done ({len(paths)} file(s)), mode={args.mode}.")


if __name__ == "__main__":
    main()
