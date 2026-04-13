"""
UCLM thermal handgun dataset layout (under UCLM_Thermal_Imaging_Dataset/):

  Handgun/<sequence_id>/video.mp4  -> label unsafe (handgun present)
  No_Gun/<sequence_id>/video.mp4   -> label safe

Each sequence may also contain label.json (detection annotations); we only use full-frame
classification from the thermal video, matching scripts.weapon_tools.train.
"""

from __future__ import annotations

from pathlib import Path

from .manifest import ManifestRow


def discover_uclm_rows(uclm_root: Path) -> list[ManifestRow]:
    uclm_root = uclm_root.resolve()
    rows: list[ManifestRow] = []
    for sub_name, label_class in ("Handgun", "unsafe"), ("No_Gun", "safe"):
        d = uclm_root / sub_name
        if not d.is_dir():
            continue
        for seq in sorted(d.iterdir()):
            if not seq.is_dir():
                continue
            vid = seq / "video.mp4"
            if vid.is_file():
                rows.append(
                    ManifestRow(
                        label_class=label_class,
                        scenario="uclm_thermal",
                        video=vid.resolve(),
                        raw={"source": "uclm", "split": sub_name, "folder": seq.name},
                    )
                )
    return rows
