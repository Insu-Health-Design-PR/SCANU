"""mmWave visualization and camera projection helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .normalized import NormalizedMmwaveFrame, NormalizedMmwaveObject


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


def render_top_down_jpeg(frame: NormalizedMmwaveFrame, output_path: str | Path, *, max_range_m: float = 12.0) -> Path:
    """Render a headless-safe top-down mmWave preview image."""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        return _render_top_down_jpeg_cv2(frame, out, max_range_m=max_range_m)
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


def _render_top_down_jpeg_cv2(frame: NormalizedMmwaveFrame, out: Path, *, max_range_m: float) -> Path:
    import cv2
    import numpy as np

    width, height = 760, 520
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (16, 12, 10)

    left, right = 70, width - 28
    top, bottom = 52, height - 54
    cv2.rectangle(img, (left, top), (right, bottom), (66, 49, 42), 1)

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

    if not frame.objects:
        cv2.putText(img, "No mmWave objects", (left + 180, top + 180), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (168, 149, 139), 2)

    for obj in frame.objects:
        u, v = px(obj)
        speed = max(-1.5, min(1.5, obj.velocity_mps))
        if speed > 0.15:
            color = (76, 170, 255)
        elif speed < -0.15:
            color = (245, 120, 91)
        else:
            color = (245, 156, 91)
        radius = int(5 + max(0.0, min(1.0, obj.confidence)) * 8)
        cv2.circle(img, (u, v), radius, color, -1)
        cv2.circle(img, (u, v), radius, (238, 241, 247), 1)
        if abs(obj.velocity_mps) > 0.01:
            dv = int(max(-28, min(28, obj.velocity_mps * -22)))
            cv2.arrowedLine(img, (u, v), (u, v + dv), (10, 159, 255), 2, tipLength=0.35)
        if obj.track_id:
            cv2.putText(img, str(obj.track_id), (u + 9, v - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (238, 241, 247), 1)

    tmp = out.with_suffix(out.suffix + ".tmp")
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    if not ok:
        raise RuntimeError("OpenCV failed to encode mmWave preview")
    tmp.write_bytes(buf.tobytes())
    tmp.replace(out)
    return out
