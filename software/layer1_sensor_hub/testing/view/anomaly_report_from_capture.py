#!/usr/bin/env python3
"""Build an anomaly report JSON from a raw capture JSON."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return float(default)
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _thermal_mean(frame: dict[str, Any]) -> float:
    thermal = frame.get("thermal") or {}
    return _safe_float(thermal.get("mean_u8"), 0.0)


def _presence_raw(frame: dict[str, Any]) -> float:
    presence = frame.get("presence") or {}
    return _safe_float(presence.get("presence_raw"), 0.0)


def _mmwave_risk(frame: dict[str, Any]) -> float:
    mm = frame.get("mmwave") or {}
    risk = (mm.get("risk_features") or {}).get("risk_score_mmwave")
    if risk is not None:
        return _clamp01(_safe_float(risk, 0.0))
    # Fallback for older capture format: weak proxy from point count.
    num_points = int(_safe_float(mm.get("num_points"), 0))
    return _clamp01(num_points / 10.0)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate anomaly report from raw capture JSON")
    p.add_argument("--capture-json", required=True, help="Path to raw capture JSON")
    p.add_argument("--output", default="", help="Output report JSON path")

    p.add_argument("--mmwave-risk-th", type=float, default=0.03)
    p.add_argument("--presence-th", type=float, default=1.0)
    p.add_argument("--thermal-delta-th", type=float, default=3.0)
    p.add_argument("--fusion-mode", default="mm_primary_temporal")
    p.add_argument("--thermal-support-window", type=int, default=10)
    p.add_argument("--thermal-support-delta-th", type=float, default=1.0)
    p.add_argument("--min-consecutive", type=int, default=2)
    p.add_argument("--thermal-baseline-frames", type=int, default=20)
    return p


def _segments_from_flags(flags: list[bool], frame_scores: list[float], mm_risks: list[float]) -> list[dict[str, Any]]:
    segs: list[dict[str, Any]] = []
    start = None
    for i, on in enumerate(flags):
        if on and start is None:
            start = i
        if not on and start is not None:
            end = i - 1
            peak_idx = max(range(start, end + 1), key=lambda k: frame_scores[k])
            segs.append(
                {
                    "start_frame": start,
                    "end_frame": end,
                    "length": end - start + 1,
                    "peak_frame": peak_idx,
                    "peak_score": frame_scores[peak_idx],
                    "peak_mmwave_risk": mm_risks[peak_idx],
                }
            )
            start = None
    if start is not None:
        end = len(flags) - 1
        peak_idx = max(range(start, end + 1), key=lambda k: frame_scores[k])
        segs.append(
            {
                "start_frame": start,
                "end_frame": end,
                "length": end - start + 1,
                "peak_frame": peak_idx,
                "peak_score": frame_scores[peak_idx],
                "peak_mmwave_risk": mm_risks[peak_idx],
            }
        )
    return segs


def _cluster_count(points: list[dict[str, Any]], radius_m: float = 0.75, min_cluster_points: int = 2) -> int:
    """Lightweight XY proximity clustering to estimate number of persons."""
    if not points:
        return 0
    xy: list[tuple[float, float]] = []
    for p in points:
        x = p.get("x")
        y = p.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            xy.append((float(x), float(y)))
    n = len(xy)
    if n == 0:
        return 0

    labels = [-1] * n
    cid = 0
    for i in range(n):
        if labels[i] != -1:
            continue
        labels[i] = cid
        queue = [i]
        while queue:
            idx = queue.pop()
            x0, y0 = xy[idx]
            for j in range(n):
                if labels[j] != -1:
                    continue
                x1, y1 = xy[j]
                if math.hypot(x1 - x0, y1 - y0) <= radius_m:
                    labels[j] = cid
                    queue.append(j)
        cid += 1

    # Keep only clusters with enough points to reduce noise spikes.
    counts: dict[int, int] = {}
    for lab in labels:
        counts[lab] = counts.get(lab, 0) + 1
    valid = [c for c in counts.values() if c >= int(min_cluster_points)]
    return len(valid)


def main() -> int:
    args = build_parser().parse_args()
    capture_path = Path(args.capture_json).expanduser().resolve()
    if not capture_path.is_file():
        raise RuntimeError(f"Capture JSON not found: {capture_path}")

    payload = json.loads(capture_path.read_text(encoding="utf-8"))
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise RuntimeError("Capture JSON does not contain a non-empty 'frames' list")

    thermal_vals = [_thermal_mean(f) for f in frames]
    baseline_n = max(1, min(len(thermal_vals), int(args.thermal_baseline_frames)))
    thermal_baseline = sum(thermal_vals[:baseline_n]) / baseline_n

    mm_risks: list[float] = []
    frame_scores: list[float] = []
    mm_candidates: list[bool] = []
    thermal_supported: list[bool] = []
    frame_cluster_counts: list[int] = []

    # Compute per-frame primitives first.
    for f in frames:
        mm = _mmwave_risk(f)
        mm_points = ((f.get("mmwave") or {}).get("points") or [])
        prs = _presence_raw(f)
        t_delta = max(0.0, _thermal_mean(f) - thermal_baseline)
        prs_norm = _clamp01(prs / max(args.presence_th, 1e-6))
        t_norm = _clamp01(t_delta / max(args.thermal_delta_th, 1e-6))
        score = _clamp01(0.75 * mm + 0.15 * prs_norm + 0.10 * t_norm)

        mm_risks.append(mm)
        frame_scores.append(score)
        mm_candidates.append(mm >= float(args.mmwave_risk_th))
        if isinstance(mm_points, list):
            frame_cluster_counts.append(_cluster_count(mm_points))
        else:
            frame_cluster_counts.append(0)

    # Add thermal support condition over trailing window.
    win = max(1, int(args.thermal_support_window))
    t_support_th = float(args.thermal_support_delta_th)
    for i in range(len(frames)):
        left = max(0, i - win + 1)
        tmax = max(max(0.0, thermal_vals[k] - thermal_baseline) for k in range(left, i + 1))
        thermal_supported.append(tmax >= t_support_th)

    suspicious = [mm_candidates[i] and thermal_supported[i] for i in range(len(frames))]
    segs = _segments_from_flags(suspicious, frame_scores, mm_risks)
    min_consecutive = max(1, int(args.min_consecutive))
    alert_segments = [s for s in segs if int(s["length"]) >= min_consecutive]

    max_consecutive = max((int(s["length"]) for s in segs), default=0)

    # Coarse entity estimates from capture-level behavior.
    nonzero_clusters = [c for c in frame_cluster_counts if c > 0]
    persons_estimated = int(round(max(nonzero_clusters) if nonzero_clusters else 0))
    # Heuristic: suspected weapons bounded by suspicious segments and persons.
    weapons_suspected = min(persons_estimated, len(alert_segments))

    report = {
        "status": "ALERT" if alert_segments else "NO_ALERT",
        "summary": {
            "frames": len(frames),
            "alerts": len(alert_segments),
            "avg_frame_score": sum(frame_scores) / len(frame_scores),
            "thermal_baseline": thermal_baseline,
            "mmwave_candidate_frames": sum(1 for v in mm_candidates if v),
            "thermal_supported_frames": sum(1 for v in thermal_supported if v),
            "suspicious_frames": sum(1 for v in suspicious if v),
            "max_consecutive_suspicious": max_consecutive,
        },
        "estimated_entities": {
            "persons_estimated": persons_estimated,
            "weapons_suspected_estimated": weapons_suspected,
            "method": "xy_cluster_heuristic_from_mmwave_points",
            "note": "Heuristic estimate only; not identity tracking.",
        },
        "thresholds": {
            "mmwave_risk_th": float(args.mmwave_risk_th),
            "presence_th": float(args.presence_th),
            "thermal_delta_th": float(args.thermal_delta_th),
            "fusion_mode": str(args.fusion_mode),
            "thermal_support_window": int(args.thermal_support_window),
            "thermal_support_delta_th": float(args.thermal_support_delta_th),
            "min_consecutive": int(args.min_consecutive),
            "thermal_baseline_frames": int(args.thermal_baseline_frames),
        },
        "capture_paths": {
            "capture_json": str(capture_path),
            "video": (payload.get("capture_info") or {}).get("video", ""),
            "risk_config": ((payload.get("capture_info") or {}).get("risk_params") or {}).get("config_path", ""),
        },
        "segments": alert_segments,
    }

    out_path = (
        Path(args.output).expanduser().resolve()
        if args.output.strip()
        else capture_path.with_name(capture_path.name.replace("_capture.json", "_report.json"))
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Saved anomaly report: {out_path}")
    print(f"status={report['status']} alerts={report['summary']['alerts']} avg_score={report['summary']['avg_frame_score']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

