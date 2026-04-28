#!/usr/bin/env python3
"""Capture thermal still images with menu-driven front/back/side labeling.

Stores all images in one output folder. The selected view is encoded in each
filename (auto-name with per-view incremental counter).
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

from software.layer1_sensor_hub.thermal import ThermalCameraSource


VIEWS = ("front_view", "back_view", "side_view")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Capture thermal images by view (front/back/side)")
    p.add_argument(
        "--out-dir",
        default="~/Desktop/collecting_data/thermal_weapon_views",
        help="Base output directory",
    )
    p.add_argument("--images-per-view", type=int, default=20, help="Target images per view")
    p.add_argument("--interval-s", type=float, default=0.35, help="Delay between saved images in auto mode")
    p.add_argument("--manual", action="store_true", help="Manual mode: press Enter for each image")
    p.add_argument("--thermal-device", type=int, default=0)
    p.add_argument("--thermal-width", type=int, default=640)
    p.add_argument("--thermal-height", type=int, default=480)
    p.add_argument("--thermal-fps", type=int, default=30)
    p.add_argument("--warmup-frames", type=int, default=8, help="Initial frames to discard")
    return p


def _ensure_dir(base: Path) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    return base


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def _next_index(out_dir: Path, view: str, session_id: str) -> int:
    patt = re.compile(rf"^thermal_{re.escape(view)}_{re.escape(session_id)}_(\d+)\.png$")
    best = 0
    for p in out_dir.glob(f"thermal_{view}_{session_id}_*.png"):
        m = patt.match(p.name)
        if m:
            best = max(best, int(m.group(1)))
    return best + 1


def _menu_pick_view() -> str | None:
    print("\nSelect view:")
    print("1) front_view")
    print("2) back_view")
    print("3) side_view")
    print("4) exit")
    c = input("> ").strip().lower()
    if c in ("1", "front", "front_view"):
        return "front_view"
    if c in ("2", "back", "back_view"):
        return "back_view"
    if c in ("3", "side", "side_view"):
        return "side_view"
    if c in ("4", "exit", "quit", "q"):
        return None
    print("Invalid option.")
    return ""


def main() -> int:
    import cv2

    args = build_parser().parse_args()
    out_dir = Path(args.out_dir).expanduser().resolve()
    _ensure_dir(out_dir)

    source = ThermalCameraSource(
        device=args.thermal_device,
        width=args.thermal_width,
        height=args.thermal_height,
        fps=args.thermal_fps,
    )
    info = source.info()

    # Warmup camera pipeline for more stable captures.
    for _ in range(max(0, int(args.warmup_frames))):
        _ = source.read_colormap_bgr()

    manifest_rows: list[dict] = []
    session_id = _timestamp()

    try:
        print("Thermal capture session")
        print(f"Session id: {session_id}")
        print(f"Output dir (single folder): {out_dir}")
        print(f"Thermal: {info.width}x{info.height} @ {info.fps:.1f} fps")
        print(f"Mode: {'manual' if args.manual else 'auto'}")
        print(f"Images per view: {args.images_per_view}")

        per_view_saved = {v: 0 for v in VIEWS}

        while True:
            print("\n" + "=" * 80)
            print(f"Progress: front={per_view_saved['front_view']} back={per_view_saved['back_view']} side={per_view_saved['side_view']}")
            view = _menu_pick_view()
            if view is None:
                break
            if view == "":
                continue

            remaining = max(0, int(args.images_per_view) - per_view_saved[view])
            if remaining == 0:
                print(f"[info] Target reached for {view}. You can still keep capturing if needed.")
                remaining = 999999

            print(f"Prepare object for: {view}")
            input("Press Enter to start capture for this view...")

            while remaining > 0:
                idx = _next_index(out_dir, view, session_id)
                if args.manual:
                    cmd = input(f"[{view}] next image #{idx}: Enter=save, skip=s, menu=m, exit=exit > ").strip().lower()
                    if cmd in ("exit", "quit", "q"):
                        raise KeyboardInterrupt
                    if cmd in ("m", "menu"):
                        break
                    if cmd in ("s", "skip"):
                        continue

                frame = source.read_colormap_bgr()
                if frame is None:
                    print(f"[warn] No thermal frame for {view}, skipping")
                    time.sleep(0.05)
                    continue

                name = f"thermal_{view}_{session_id}_{idx:04d}.png"
                path = out_dir / name
                ok = cv2.imwrite(str(path), frame)
                if not ok:
                    print(f"[warn] Failed to write image: {path}")
                    continue

                per_view_saved[view] += 1
                remaining -= 1
                manifest_rows.append(
                    {
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat(),
                        "view": view,
                        "index": idx,
                        "path": str(path),
                        "thermal_device": int(args.thermal_device),
                        "thermal_width": int(info.width),
                        "thermal_height": int(info.height),
                        "thermal_fps": float(info.fps),
                    }
                )
                print(f"[saved] {path}")
                if not args.manual:
                    time.sleep(max(0.0, float(args.interval_s)))

            # If auto mode, return to menu after target count for selected view.
            if not args.manual:
                print(f"[info] Returning to menu for next view selection.")

        manifest_path = out_dir / f"thermal_weapon_views_manifest_{session_id}.json"
        manifest_payload = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "images_per_view_requested": int(args.images_per_view),
            "mode": "manual" if args.manual else "auto",
            "views": list(VIEWS),
            "saved_per_view": per_view_saved,
            "rows": manifest_rows,
        }
        manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

        print("\n" + "=" * 80)
        print("Capture completed.")
        print(f"Images saved: {len(manifest_rows)}")
        print(f"Manifest: {manifest_path}")
        print("=" * 80)
        return 0

    except KeyboardInterrupt:
        print("\nCapture interrupted by user.")
        return 0
    finally:
        source.close()


if __name__ == "__main__":
    raise SystemExit(main())
