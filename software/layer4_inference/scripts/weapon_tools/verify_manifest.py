"""List manifest entries and whether each video file exists under --data_root."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from .manifest import iter_existing_videos, load_manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data_root", type=Path, default=Path("data"))
    p.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/collecting_data/manifest.jsonl"),
    )
    args = p.parse_args()
    manifest_path = args.manifest
    if not manifest_path.is_file():
        manifest_path = args.data_root / "collecting_data" / "manifest.jsonl"
    rows = load_manifest(manifest_path, args.data_root)
    existing = list(iter_existing_videos(rows))
    labels = Counter(r.label_class for r in rows)
    ok_labels = Counter(r.label_class for r in existing)
    print(f"Manifest: {manifest_path}")
    print(f"Entries: {len(rows)} | labels: {dict(labels)}")
    print(f"Videos found: {len(existing)} | labels (with files): {dict(ok_labels)}")
    for r in rows:
        status = "OK" if r.video.is_file() else "MISSING"
        print(f"  [{status}] {r.label_class:7} {r.video}")


if __name__ == "__main__":
    main()
