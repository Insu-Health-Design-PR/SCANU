"""
Discover thermal-only training clips under collecting_data/.

Picks up:
  - .../safe/.../anything_thermal.mp4 (flat split from split_panels)
  - .../unsafe/.../anything_thermal.mp4
  - Legacy: .../stem_panels/thermal.mp4 (skipped if stem_thermal.mp4 exists beside the folder)
"""

from __future__ import annotations

from pathlib import Path

from .manifest import ManifestRow


def _label_from_collecting_path(path: Path, collecting_root: Path) -> int | None:
    try:
        rel = path.resolve().relative_to(collecting_root.resolve())
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 2:
        return None
    bucket = parts[0]
    if bucket == "safe":
        return 0
    if bucket == "unsafe":
        return 1
    return None


def discover_thermal_training_rows(collecting_data: Path) -> list[ManifestRow]:
    collecting_data = collecting_data.resolve()
    if not collecting_data.is_dir():
        return []

    seen: set[Path] = set()
    rows: list[ManifestRow] = []

    for p in sorted(collecting_data.rglob("*_thermal.mp4")):
        if not p.is_file():
            continue
        lid = _label_from_collecting_path(p, collecting_data)
        if lid is None:
            continue
        r = p.resolve()
        if r in seen:
            continue
        seen.add(r)
        rows.append(
            ManifestRow(
                label_class="safe" if lid == 0 else "unsafe",
                scenario="thermal_mp4",
                video=r,
                raw={"source": "flat_thermal"},
            )
        )

    for p in sorted(collecting_data.rglob("thermal.mp4")):
        if not p.is_file():
            continue
        parent = p.parent
        if not parent.name.endswith("_panels"):
            continue
        stem = parent.name[: -len("_panels")]
        flat_sibling = parent.parent / f"{stem}_thermal.mp4"
        if flat_sibling.is_file():
            continue
        lid = _label_from_collecting_path(p, collecting_data)
        if lid is None:
            continue
        r = p.resolve()
        if r in seen:
            continue
        seen.add(r)
        rows.append(
            ManifestRow(
                label_class="safe" if lid == 0 else "unsafe",
                scenario="thermal_panels",
                video=r,
                raw={"source": "panels_folder"},
            )
        )

    return rows
