"""mmWave visualization and camera projection helpers."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .normalized import NormalizedMmwaveFrame, NormalizedMmwaveObject
from .zone_config import ZoneConfig


@dataclass
class MovementTrail:
    track_id: str
    positions: list[tuple[float, float, float]] = field(default_factory=list)
    max_length: int = 15


class MovementTrailTracker:
    """Tracks object positions across frames per track_id for trail rendering."""

    def __init__(self, max_trail_length: int = 15) -> None:
        self._trails: dict[str, MovementTrail] = {}
        self._max_length = max_trail_length

    def update(self, frame: NormalizedMmwaveFrame) -> None:
        seen: set[str] = set()
        for obj in frame.objects:
            tid = obj.track_id
            if tid is None:
                continue
            seen.add(tid)
            if tid not in self._trails:
                self._trails[tid] = MovementTrail(track_id=tid, max_length=self._max_length)
            trail = self._trails[tid]
            trail.positions.append((obj.x, obj.y, obj.range_m))
            if len(trail.positions) > self._max_length:
                trail.positions.pop(0)
        for tid in list(self._trails.keys()):
            if tid not in seen:
                self._trails.pop(tid, None)

    def get_trail(self, track_id: str) -> list[tuple[float, float, float]]:
        trail = self._trails.get(track_id)
        return list(trail.positions) if trail is not None else []

    def clear(self) -> None:
        self._trails.clear()


@dataclass
class CameraProjectionConfig:
    width: int = 1280
    height: int = 720
    x_scale_px_per_m: float = 120.0
    y_scale_px_per_m: float = 90.0
    x_offset_px: float = 0.0
    y_offset_px: float = 0.0
    rotation_deg: float = 0.0
    max_range_m: float = 12.0

    @classmethod
    def from_mapping(cls, values: dict[str, Any] | None) -> "CameraProjectionConfig":
        if not isinstance(values, dict):
            return cls()

        def f(key: str, default: float) -> float:
            try:
                return float(values.get(key, default))
            except (TypeError, ValueError):
                return default

        def i(key: str, default: int) -> int:
            try:
                return int(values.get(key, default))
            except (TypeError, ValueError):
                return default

        return cls(
            width=i("width", cls.width),
            height=i("height", cls.height),
            x_scale_px_per_m=f("x_scale_px_per_m", cls.x_scale_px_per_m),
            y_scale_px_per_m=f("y_scale_px_per_m", cls.y_scale_px_per_m),
            x_offset_px=f("x_offset_px", cls.x_offset_px),
            y_offset_px=f("y_offset_px", cls.y_offset_px),
            rotation_deg=f("rotation_deg", cls.rotation_deg),
            max_range_m=f("max_range_m", cls.max_range_m),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "x_scale_px_per_m": self.x_scale_px_per_m,
            "y_scale_px_per_m": self.y_scale_px_per_m,
            "x_offset_px": self.x_offset_px,
            "y_offset_px": self.y_offset_px,
            "rotation_deg": self.rotation_deg,
            "max_range_m": self.max_range_m,
        }


def project_object_to_camera(obj: NormalizedMmwaveObject, cfg: CameraProjectionConfig) -> dict[str, Any]:
    """Project top-down radar x/y into simple camera overlay coordinates."""

    theta = math.radians(cfg.rotation_deg)
    xr = (obj.x * math.cos(theta)) - (obj.y * math.sin(theta))
    yr = (obj.x * math.sin(theta)) + (obj.y * math.cos(theta))

    u = (cfg.width / 2.0) + cfg.x_offset_px + (xr * cfg.x_scale_px_per_m)
    v = cfg.height - cfg.y_offset_px - (yr * cfg.y_scale_px_per_m)
    u = max(0.0, min(float(cfg.width), u))
    v = max(0.0, min(float(cfg.height), v))

    return {
        "x_px": u,
        "y_px": v,
        "x_norm": u / max(1.0, float(cfg.width)),
        "y_norm": v / max(1.0, float(cfg.height)),
        "range_m": obj.range_m,
        "velocity_mps": obj.velocity_mps,
        "confidence": obj.confidence,
        "track_id": obj.track_id,
    }


def project_frame_to_camera(frame: NormalizedMmwaveFrame, cfg: CameraProjectionConfig) -> dict[str, Any]:
    return {
        "frame_id": frame.frame_id,
        "timestamp_ms": frame.timestamp_ms,
        "radar_id": frame.radar_id,
        "image": {"width": cfg.width, "height": cfg.height},
        "calibration": cfg.to_dict(),
        "points": [project_object_to_camera(obj, cfg) for obj in frame.objects],
    }


def _in_any_zone(rng_m: float, zones: list[ZoneConfig]) -> bool:
    return any(z.contains(rng_m) for z in zones)


def _zone_color(rng_m: float, vel: float, zones: list[ZoneConfig]) -> tuple[int, int, int]:
    for z in zones:
        if z.contains(rng_m):
            return z.color
    if abs(vel) > 0.3:
        return (50, 200, 50)
    return (200, 200, 50)


def _zone_label(rng_m: float, zones: list[ZoneConfig]) -> str:
    for z in zones:
        if z.contains(rng_m):
            return z.label
    return ""


def render_mmwave_camera_overlay(
    camera_bgr: Any,
    frame: NormalizedMmwaveFrame,
    cfg: CameraProjectionConfig,
    *,
    show_trails: bool = True,
    trail_tracker: MovementTrailTracker | None = None,
    show_labels: bool = True,
    show_velocity_arrows: bool = True,
    zones: list[ZoneConfig] | None = None,
    trail_color: tuple[int, int, int] = (200, 200, 80),
) -> Any:
    """Overlay mmWave projected objects onto a camera frame (BGR)."""
    import cv2
    import numpy as np

    zones = zones or [ZoneConfig(name="weapon", range_min_m=1.17, range_max_m=1.95, color=(50, 50, 220), label="W")]
    out = camera_bgr.copy()
    overlay = project_frame_to_camera(frame, cfg)
    h, w = out.shape[:2]

    # draw trails
    if show_trails and trail_tracker is not None:
        for obj in frame.objects:
            tid = obj.track_id
            if tid is None:
                continue
            trail_positions = trail_tracker.get_trail(tid)
            if len(trail_positions) < 2:
                continue
            trail_px: list[tuple[int, int]] = []
            for tx, ty, _ in trail_positions:
                theta = math.radians(cfg.rotation_deg)
                xr = (tx * math.cos(theta)) - (ty * math.sin(theta))
                yr = (tx * math.sin(theta)) + (ty * math.cos(theta))
                u = int((cfg.width / 2.0) + cfg.x_offset_px + (xr * cfg.x_scale_px_per_m))
                v = int(cfg.height - cfg.y_offset_px - (yr * cfg.y_scale_px_per_m))
                u = max(0, min(int(w), u))
                v = max(0, min(int(h), v))
                trail_px.append((u, v))
            for i in range(1, len(trail_px)):
                alpha = i / max(1, len(trail_px))
                thickness = max(1, int(3 * alpha))
                cv2.line(out, trail_px[i - 1], trail_px[i], trail_color, thickness, cv2.LINE_AA)

    # draw projected points
    for pt in overlay["points"]:
        u = int(round(pt["x_px"]))
        v = int(round(pt["y_px"]))
        if u < 0 or u >= w or v < 0 or v >= h:
            continue
        conf = float(pt.get("confidence", 0.5))
        vel = float(pt.get("velocity_mps", 0.0))
        rng_m = float(pt.get("range_m", 0.0))
        color = _zone_color(rng_m, vel, zones)

        radius = max(3, int(6 * conf))
        cv2.circle(out, (u, v), radius, color, -1)
        cv2.circle(out, (u, v), radius + 1, (255, 255, 255), 1)

        if show_velocity_arrows and abs(vel) > 0.05:
            dx = int(vel * 30)
            cv2.arrowedLine(out, (u, v), (u + dx, v), (0, 200, 255), 2, tipLength=0.3)

        if show_labels:
            label = ""
            if pt.get("track_id"):
                label = str(pt["track_id"])
            zl = _zone_label(rng_m, zones)
            if zl:
                label = (label + " " + zl if label else zl)
            if label:
                cv2.putText(out, label, (u + radius + 3, v - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    return out


def render_top_down_jpeg(
    frame: NormalizedMmwaveFrame,
    output_path: str | Path,
    *,
    max_range_m: float = 12.0,
    trail_tracker: MovementTrailTracker | None = None,
    zones: list[ZoneConfig] | None = None,
) -> Path:
    """Render a headless-safe top-down mmWave preview image."""

    zones = zones or [ZoneConfig(name="weapon", range_min_m=1.17, range_max_m=1.95, color=(50, 50, 220), label="W")]
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    weapon_zone_m = (zones[0].range_min_m, zones[0].range_max_m) if zones else (1.17, 1.95)
    try:
        return _render_top_down_jpeg_cv2(frame, out, max_range_m=max_range_m, trail_tracker=trail_tracker, weapon_zone_m=weapon_zone_m)
    except Exception:
        pass

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    xs = np.asarray([obj.x for obj in frame.objects], dtype=np.float32)
    ys = np.asarray([obj.y for obj in frame.objects], dtype=np.float32)
    vel = np.asarray([obj.velocity_mps for obj in frame.objects], dtype=np.float32)
    conf = np.asarray([obj.confidence for obj in frame.objects], dtype=np.float32)

    fig, ax = plt.subplots(figsize=(6, 4.5), facecolor="#0a0c10")
    ax.set_facecolor("#0a0c10")
    ax.set_title(f"mmWave frame {frame.frame_id} · objects {len(frame.objects)}", color="#eef1f7", fontsize=11)
    ax.set_xlabel("x lateral (m)", color="#8b95a8")
    ax.set_ylabel("y range (m)", color="#8b95a8")
    ax.set_xlim(-max_range_m / 2.0, max_range_m / 2.0)
    ax.set_ylim(0.0, max_range_m)
    ax.grid(True, color="#2a3142", alpha=0.7)
    ax.tick_params(colors="#8b95a8")

    if frame.objects:
        sizes = 45.0 + (np.clip(conf, 0.0, 1.0) * 80.0)
        sc = ax.scatter(xs, ys, c=vel, s=sizes, cmap="coolwarm", vmin=-1.5, vmax=1.5, edgecolors="#eef1f7", linewidths=0.4)
        for obj in frame.objects:
            if abs(obj.velocity_mps) > 0.01:
                ax.arrow(
                    obj.x,
                    obj.y,
                    0.0,
                    max(-0.35, min(0.35, obj.velocity_mps * 0.25)),
                    head_width=0.08,
                    head_length=0.12,
                    fc="#ff9f0a",
                    ec="#ff9f0a",
                    alpha=0.75,
                )
            if obj.track_id:
                ax.text(obj.x, obj.y + 0.2, str(obj.track_id), color="#eef1f7", fontsize=8, ha="center")
        cbar = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("velocity m/s", color="#8b95a8")
        cbar.ax.yaxis.set_tick_params(color="#8b95a8")
        plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="#8b95a8")
    else:
        ax.text(0.0, max_range_m * 0.5, "No mmWave objects", color="#8b95a8", ha="center", va="center")

    fig.tight_layout()
    tmp = out.with_suffix(out.suffix + ".tmp")
    fig.savefig(tmp, dpi=140, facecolor=fig.get_facecolor(), format="jpg")
    plt.close(fig)
    tmp.replace(out)
    return out


def _render_top_down_jpeg_cv2(
    frame: NormalizedMmwaveFrame,
    out: Path,
    *,
    max_range_m: float,
    trail_tracker: MovementTrailTracker | None = None,
    weapon_zone_m: tuple[float, float] = (1.17, 1.95),
) -> Path:
    import cv2
    import numpy as np

    width, height = 760, 520
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (16, 12, 10)

    left, right = 70, width - 28
    top, bottom = 52, height - 54
    cv2.rectangle(img, (left, top), (right, bottom), (66, 49, 42), 1)

    # weapon zone highlight (range band)
    zone_top = int(bottom - (weapon_zone_m[1] / max_range_m) * (bottom - top))
    zone_bottom_val = int(bottom - (weapon_zone_m[0] / max_range_m) * (bottom - top))
    if zone_top < zone_bottom_val:
        cv2.rectangle(img, (left, zone_top), (right, zone_bottom_val), (30, 30, 80), -1)

    for i in range(1, 5):
        y = int(bottom - (i / 4.0) * (bottom - top))
        cv2.line(img, (left, y), (right, y), (42, 49, 66), 1)
        cv2.putText(img, f"{max_range_m * i / 4.0:.0f}m", (12, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (168, 149, 139), 1)

    cv2.putText(
        img,
        f"mmWave frame {frame.frame_id} | objects {len(frame.objects)}",
        (left, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (247, 241, 238),
        2,
    )

    def px(obj: NormalizedMmwaveObject) -> tuple[int, int]:
        x_norm = (obj.x + (max_range_m / 2.0)) / max(0.1, max_range_m)
        y_norm = obj.y / max(0.1, max_range_m)
        u = int(left + max(0.0, min(1.0, x_norm)) * (right - left))
        v = int(bottom - max(0.0, min(1.0, y_norm)) * (bottom - top))
        return u, v

    # draw trails
    if trail_tracker is not None:
        for obj in frame.objects:
            tid = obj.track_id
            if tid is None:
                continue
            trail = trail_tracker.get_trail(tid)
            if len(trail) < 2:
                continue
            trail_px: list[tuple[int, int]] = []
            for tx, ty, _ in trail:
                xn = (tx + (max_range_m / 2.0)) / max(0.1, max_range_m)
                yn = ty / max(0.1, max_range_m)
                tu = int(left + max(0.0, min(1.0, xn)) * (right - left))
                tv = int(bottom - max(0.0, min(1.0, yn)) * (bottom - top))
                trail_px.append((tu, tv))
            for i in range(1, len(trail_px)):
                alpha = i / max(1, len(trail_px))
                thickness = max(1, int(3 * alpha))
                cv2.line(img, trail_px[i - 1], trail_px[i], (80, 200, 200), thickness, cv2.LINE_AA)

    if not frame.objects:
        cv2.putText(img, "No mmWave objects", (left + 180, top + 180), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (168, 149, 139), 2)

    for obj in frame.objects:
        u, v = px(obj)
        speed = max(-1.5, min(1.5, obj.velocity_mps))
        in_weapon_zone = weapon_zone_m[0] <= obj.range_m <= weapon_zone_m[1]

        if in_weapon_zone:
            color = (50, 50, 220)
        elif speed > 0.15:
            color = (76, 170, 255)
        elif speed < -0.15:
            color = (245, 120, 91)
        else:
            color = (245, 156, 91)
        radius = int(5 + max(0.0, min(1.0, obj.confidence)) * 8)
        cv2.circle(img, (u, v), radius, color, -1)
        cv2.circle(img, (u, v), radius, (238, 241, 247), 1)

        # velocity arrow: 2D using doppler as proxy for range-rate
        if abs(obj.velocity_mps) > 0.05:
            dx = int((obj.x / max(0.1, max_range_m)) * obj.velocity_mps * -28)
            dy = int(obj.velocity_mps * -22)
            if abs(dx) + abs(dy) > 3:
                cv2.arrowedLine(img, (u, v), (u + dx, v + dy), (10, 159, 255), 2, tipLength=0.3)

        # weapon zone marker
        if in_weapon_zone:
            cv2.putText(img, "W", (u + 9, v - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 220), 1)

        if obj.track_id:
            cv2.putText(img, str(obj.track_id), (u + 9, v - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (238, 241, 247), 1)

    # scale bar
    scale_x = left
    scale_y = height - 18
    scale_len_px = int(70)
    cv2.line(img, (scale_x, scale_y), (scale_x + scale_len_px, scale_y), (168, 149, 139), 2)
    scale_m = (scale_len_px / (right - left)) * max_range_m
    cv2.putText(img, f"{scale_m:.1f}m", (scale_x + scale_len_px + 4, scale_y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (168, 149, 139), 1)

    tmp = out.with_suffix(out.suffix + ".tmp")
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    if not ok:
        raise RuntimeError("OpenCV failed to encode mmWave preview")
    tmp.write_bytes(buf.tobytes())
    tmp.replace(out)
    return out
