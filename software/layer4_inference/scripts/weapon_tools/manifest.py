from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .paths import resolve_collecting_path


@dataclass(frozen=True)
class ManifestRow:
    label_class: str  # "safe" | "unsafe"
    scenario: str
    video: Path
    raw: dict

    @property
    def label_id(self) -> int:
        return 0 if self.label_class == "safe" else 1


def load_manifest(manifest_path: Path, data_root: Path) -> list[ManifestRow]:
    rows: list[ManifestRow] = []
    with manifest_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            vp = resolve_collecting_path(obj["video"], data_root)
            rows.append(
                ManifestRow(
                    label_class=obj["label_class"],
                    scenario=obj.get("scenario", ""),
                    video=vp,
                    raw=obj,
                )
            )
    return rows


def iter_existing_videos(rows: list[ManifestRow]) -> Iterator[ManifestRow]:
    for r in rows:
        if r.video.is_file():
            yield r
