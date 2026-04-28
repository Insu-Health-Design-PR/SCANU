"""
Split composite MP4s (3 side-by-side panels) into separate videos: thermal, mmwave, infineon.

Default layout: three equal-width columns, left-to-right order thermal | mmwave | infineon.
Override with --order if your recorder uses a different arrangement.

Examples:
  python -m scripts.weapon_tools.split_panels --input data/collecting_data/safe/foo/foo.mp4
  python -m scripts.weapon_tools.split_panels --data_root data --recursive --dry_run

Outputs (next to the source by default): clip_thermal.mp4, clip_mmwave.mp4, clip_infineon.mp4
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def _open_writer(
    path: Path,
    fps: float,
    frame_size: tuple[int, int],
    codec_preference: list[str],
) -> tuple[cv2.VideoWriter, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = frame_size
    for codec in codec_preference:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
        if writer.isOpened():
            return writer, codec
        writer.release()
    raise RuntimeError(f"Could not open VideoWriter for {path}; tried codecs {codec_preference}")


def split_horizontal_thirds(bgr: np.ndarray) -> list[np.ndarray]:
    h, w = bgr.shape[:2]
    c = w // 3
    r = w - 3 * c
    # Put remainder in the last panel so widths sum to w
    w0, w1, w2 = c, c, c + r
    x0, x1, x2, x3 = 0, w0, w0 + w1, w0 + w1 + w2
    return [bgr[:, x0:x1], bgr[:, x1:x2], bgr[:, x2:x3]]


def split_vertical_thirds(bgr: np.ndarray) -> list[np.ndarray]:
    h, w = bgr.shape[:2]
    r_ = h // 3
    r = h - 3 * r_
    h0, h1, h2 = r_, r_, r_ + r
    y0, y1, y2, y3 = 0, h0, h0 + h1, h0 + h1 + h2
    return [bgr[y0:y1, :], bgr[y1:y2, :], bgr[y2:y3, :]]


def process_one_video(
    src: Path,
    out_parent: Path,
    out_stem: str,
    order: list[str],
    orientation: str,
    codec_preference: list[str],
    dry_run: bool,
) -> None:
    if len(order) != 3:
        raise ValueError("order must have exactly 3 names, e.g. thermal,mmwave,infineon")
    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        print(f"SKIP (cannot open): {src}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 1e-3:
        fps = 30.0

    ok, first = cap.read()
    if not ok or first is None:
        cap.release()
        print(f"SKIP (empty): {src}")
        return

    if orientation == "horizontal":
        panels = split_horizontal_thirds(first)
    else:
        panels = split_vertical_thirds(first)

    name_map = {order[i]: panels[i] for i in range(3)}
    sizes = {k: (p.shape[1], p.shape[0]) for k, p in name_map.items()}

    out_paths = {k: out_parent / f"{out_stem}_{k}.mp4" for k in order}
    listed = ", ".join(p.name for p in out_paths.values())
    print(f"{src} -> {listed}")

    if dry_run:
        cap.release()
        return

    writers: dict[str, cv2.VideoWriter] = {}
    used_codec: str | None = None
    try:
        for k in order:
            wri, used_codec = _open_writer(out_paths[k], fps, sizes[k], codec_preference)
            writers[k] = wri

        def write_frame(bgr: np.ndarray) -> None:
            if orientation == "horizontal":
                parts = split_horizontal_thirds(bgr)
            else:
                parts = split_vertical_thirds(bgr)
            for i, key in enumerate(order):
                writers[key].write(parts[i])

        write_frame(first)
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            write_frame(frame)
    finally:
        cap.release()
        for wri in writers.values():
            wri.release()


def collect_mp4s(root: Path, recursive: bool, split_suffixes: tuple[str, ...]) -> list[Path]:
    def is_skipped(p: Path) -> bool:
        if any(part.endswith("_panels") for part in p.parts):
            return True
        stem = p.stem
        return any(stem.endswith(f"_{s}") for s in split_suffixes)

    if recursive:
        found = [p for p in root.rglob("*.mp4") if not is_skipped(p)]
    else:
        found = [p for p in root.glob("*.mp4") if not is_skipped(p)]
    return sorted(found)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, help="Single MP4 file")
    p.add_argument("--data_root", type=Path, help="Root folder to scan (e.g. data)")
    p.add_argument(
        "--recursive",
        action="store_true",
        help="With --data_root, find all .mp4 under it (e.g. data/collecting_data/...)",
    )
    p.add_argument(
        "--order",
        type=str,
        default="thermal,mmwave,infineon",
        help="Comma names for left-to-right (horizontal) or top-to-bottom (vertical) panels",
    )
    p.add_argument(
        "--orientation",
        choices=["horizontal", "vertical"],
        default="horizontal",
        help="Panel layout: three columns or three rows",
    )
    p.add_argument(
        "--out_dir",
        type=Path,
        default=None,
        help="Output directory for split files. Default: same folder as the source video.",
    )
    p.add_argument(
        "--batch_out_parent",
        type=Path,
        default=None,
        help="With --data_root: write into <batch_out_parent>/<relative_dir>/ using the same "
        "<stem>_<panel>.mp4 names. Default: same directory as each source video.",
    )
    p.add_argument(
        "--codec_try",
        type=str,
        default="mp4v,avc1,X264",
        help="Comma-separated OpenCV fourcc attempts for .mp4",
    )
    p.add_argument("--dry_run", action="store_true", help="List actions only")
    args = p.parse_args()

    order = [x.strip() for x in args.order.split(",") if x.strip()]
    if len(order) != 3:
        raise SystemExit("--order must list exactly 3 comma-separated names, e.g. thermal,mmwave,infineon")
    codecs = [c.strip().ljust(4)[:4] for c in args.codec_try.split(",") if c.strip()]
    split_suffixes = tuple(order)

    if args.input:
        src = args.input.resolve()
        if not src.is_file():
            raise SystemExit(f"Not a file: {src}")
        out_parent = (args.out_dir or src.parent).resolve()
        process_one_video(
            src, out_parent, src.stem, order, args.orientation, codecs, args.dry_run
        )
        return

    if args.data_root:
        root = args.data_root.resolve()
        if not root.is_dir():
            raise SystemExit(f"Not a directory: {root}")
        videos = collect_mp4s(root, args.recursive, split_suffixes)
        if not videos:
            print(f"No .mp4 files under {root}" + (" (recursive)" if args.recursive else ""))
            return
        for src in videos:
            if args.batch_out_parent is not None:
                try:
                    rel = src.relative_to(root)
                except ValueError:
                    rel = Path(src.name)
                stem_path = rel.with_suffix("")
                out_parent = (args.batch_out_parent / stem_path.parent).resolve()
            else:
                out_parent = src.parent.resolve()
            process_one_video(
                src, out_parent, src.stem, order, args.orientation, codecs, args.dry_run
            )
        print(f"Done. Processed {len(videos)} file(s).")
        return

    raise SystemExit("Provide --input path/to/video.mp4 OR --data_root data [--recursive]")


if __name__ == "__main__":
    main()
