"""v4l2-ctl helpers for the Layer 8 dashboard (auto-detect, format lists)."""

from __future__ import annotations

import glob
import re
import subprocess
from pathlib import Path
from typing import Any


def _parse_list_devices_text(text: str) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    current_name: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            current_name = None
            continue
        m = re.match(r"^/dev/(video\d+)", line.lstrip())
        if m and current_name is not None:
            idx = int(m.group(1).replace("video", ""))
            if groups and groups[-1].get("name") == current_name:
                if idx not in groups[-1]["indices"]:
                    groups[-1]["indices"].append(idx)
            else:
                groups.append(
                    {
                        "name": current_name,
                        "indices": [idx],
                        "nodes": [f"/dev/video{idx}"],
                    }
                )
            continue
        if line and not line.startswith(("\t", " ")):
            current_name = line.strip()
    for g in groups:
        g["indices"] = sorted(set(g["indices"]))
    return groups


def list_v4l2_groups() -> dict[str, Any]:
    text = ""
    try:
        p = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        text = p.stdout or ""
        if p.returncode != 0 and not text.strip():
            return {
                "ok": False,
                "error": (p.stderr or f"v4l2-ctl exit {p.returncode}").strip(),
                "groups": [],
            }
    except FileNotFoundError:
        return {"ok": False, "error": "v4l2-ctl not installed", "groups": _fallback_glob_video_groups()}
    except (subprocess.SubprocessError, OSError) as e:
        return {"ok": False, "error": str(e), "groups": []}

    if not text.strip():
        groups = _fallback_glob_video_groups()
    else:
        groups = _parse_list_devices_text(text)
    if not groups:
        groups = _fallback_glob_video_groups()

    usb_pat = re.compile(r"(?i)usb|uvc|webcam|camera|nexigo")
    g_sorted = sorted(
        [g for g in groups if g.get("indices")],
        key=lambda g: min(g["indices"]),
    )
    suggested_webcam: int | None = None
    suggested_thermal: int | None = None
    warn = ""
    if len(g_sorted) >= 2:
        suggested_thermal = int(min(g_sorted[0]["indices"]))
        uvc = [g for g in g_sorted if usb_pat.search(g.get("name", ""))]
        if uvc:
            suggested_webcam = int(min(uvc[0]["indices"]))
        else:
            suggested_webcam = int(min(g_sorted[-1]["indices"]))
    elif g_sorted:
        n = int(min(g_sorted[0]["indices"]))
        suggested_thermal = n
        if usb_pat.search(g_sorted[0].get("name", "")) and g_sorted[0].get("indices", []):
            suggested_webcam = int(g_sorted[0]["indices"][-1])
        else:
            suggested_webcam = n
        warn = "Single V4L2 group: thermal and webcam may use the same node; use two USB cameras to separate."
    all_indices: list[int] = []
    for g in g_sorted:
        for i in g.get("indices", []):
            if int(i) not in all_indices:
                all_indices.append(int(i))
    all_indices.sort()
    if suggested_thermal is not None and suggested_webcam is not None and suggested_thermal == suggested_webcam and len(
        all_indices
    ) > 1:
        suggested_thermal, suggested_webcam = all_indices[0], all_indices[-1]

    return {
        "ok": True,
        "raw": text,
        "groups": g_sorted,
        "all_indices": all_indices,
        "suggested_thermal": suggested_thermal,
        "suggested_webcam": suggested_webcam,
        "warning": warn,
    }


def _fallback_glob_video_groups() -> list[dict[str, Any]]:
    nodes = sorted(
        glob.glob("/dev/video*"),
        key=lambda p: int(re.sub(r"^\D+", "", Path(p).name) or 0),
    )
    if not nodes:
        return []
    inds: list[int] = []
    for p in nodes:
        try:
            inds.append(int(re.sub(r"^\D+", "", Path(p).name) or 0))
        except ValueError:
            continue
    return [
        {
            "name": "Enumerated (no v4l2-ctl or empty list)",
            "indices": inds,
            "nodes": nodes,
        }
    ]


def list_formats_for_index(index: int) -> dict[str, Any]:
    path = f"/dev/video{int(index)}"
    if not Path(path).exists():
        return {
            "ok": False,
            "error": f"{path} not found",
            "options": _default_resolution_options(),
        }
    try:
        p = subprocess.run(
            ["v4l2-ctl", "-d", path, "--list-formats-ext"],
            capture_output=True,
            text=True,
            timeout=12,
        )
        out = p.stdout or ""
    except FileNotFoundError:
        return {"ok": False, "error": "v4l2-ctl not installed", "options": _default_resolution_options()}
    except (subprocess.SubprocessError, OSError) as e:
        return {"ok": False, "error": str(e), "options": _default_resolution_options()}

    options = _parse_formats_ext(out)
    if not options:
        options = _default_resolution_options()
    return {"ok": p.returncode == 0, "raw": out, "options": options}


def _parse_formats_ext(text: str) -> list[dict[str, Any]]:
    """Extract discrete WxH and fps from v4l2-ctl --list-formats-ext."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[int, int, int]] = set()
    w = h = 0
    for line in text.splitlines():
        m = re.search(r"Size: Discrete (\d+)x(\d+)", line)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
            continue
        m2 = re.search(r"\(([\d.]+) fps\)", line)
        if m2 and w > 0 and h > 0:
            fps = int(float(m2.group(1)))
            k = (w, h, fps)
            if k not in seen:
                seen.add(k)
                out.append(
                    {
                        "label": f"{w}×{h} @ {fps} fps",
                        "width": w,
                        "height": h,
                        "fps": float(fps),
                    }
                )
    out.sort(key=lambda o: (o["width"] * o["height"], o["fps"]), reverse=True)
    return out[:50]


def _default_resolution_options() -> list[dict[str, Any]]:
    """Fallback when v4l2-ctl is missing or returns nothing."""
    rows = [
        (3840, 2160, 30, "4K 3840×2160 @ 30"),
        (2560, 1440, 30, "1440p 2560×1440 @ 30"),
        (1920, 1080, 30, "1080p 1920×1080 @ 30"),
        (1280, 720, 30, "720p 1280×720 @ 30"),
        (640, 480, 30, "VGA 640×480 @ 30"),
    ]
    r = []
    for w, h, fps, label in rows:
        r.append({"label": label, "width": w, "height": h, "fps": float(fps)})
    return r


def list_serial_port_candidates() -> dict[str, Any]:
    """Prefer two ``ttyUSB*`` nodes (common for mmWave DCA) when present."""
    usb = sorted(glob.glob("/dev/ttyUSB*"), key=natural_path_sort)
    all_s = sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"), key=natural_path_sort)
    if len(usb) >= 2:
        cli, data = usb[0], usb[1]
    elif len(all_s) >= 2:
        cli, data = all_s[0], all_s[1]
    elif all_s:
        cli, data = all_s[0], all_s[0]
    else:
        cli, data = "/dev/ttyUSB0", "/dev/ttyUSB1"
    return {"ok": True, "ports": all_s, "suggested_cli": cli, "suggested_data": data}


def natural_path_sort(p: str) -> tuple[int, str]:
    m = re.search(r"(\d+)$", p)
    return (int(m.group(1)) if m else 0, p)
