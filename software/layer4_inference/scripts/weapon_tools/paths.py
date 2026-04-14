from __future__ import annotations

from pathlib import Path


def resolve_collecting_path(stored_path: str, data_root: Path) -> Path:
    """
    Map a path recorded on Linux (e.g. .../collecting_data/safe/.../file.mp4)
    to a local file under data_root (e.g. data_root/collecting_data/...).
    """
    parts = Path(stored_path).parts
    if "collecting_data" in parts:
        i = parts.index("collecting_data")
        return (data_root / Path(*parts[i:])).resolve()
    return (data_root / "collecting_data" / Path(stored_path).name).resolve()
