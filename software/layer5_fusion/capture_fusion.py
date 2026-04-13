"""Fuse mmWave capture JSON + Layer 4 thermal decisions into a structured report JSON."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import cv2

_SOFTWARE_ROOT = Path(__file__).resolve().parents[1]
if str(_SOFTWARE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOFTWARE_ROOT))

from layer4_inference.weapon_ai.threat_engine import AnomalyScorer, InferenceEngine, ThermalThreatDetector


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
    num_points = int(_safe_float(mm.get("num_points"), 0))
    return _clamp01(num_points / 10.0)


def _l4_label_to_public(label: str) -> str:
    """Expose user-facing threat vocabulary on the fusion boundary."""
    t = str(label).strip().lower()
    if t == "armed":
        return "threat"
    if t == "suspicious":
        return "suspicious"
    return "no_threat"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Layer 5: generate fused anomaly report from raw capture JSON")
    p.add_argument("--capture-json", required=True, help="Path to raw capture JSON")
    p.add_argument("--output", default="", help="Output report JSON path")
    p.add_argument("--video", default="", help="Optional override path for thermal video")

    p.add_argument("--mmwave-risk-th", type=float, default=0.03)
    p.add_argument("--presence-th", type=float, default=1.0)
    p.add_argument("--thermal-delta-th", type=float, default=3.0)
    p.add_argument("--fusion-mode", default="mm_primary_temporal")
    p.add_argument("--thermal-support-window", type=int, default=10)
    p.add_argument("--thermal-support-delta-th", type=float, default=1.0)
    p.add_argument("--min-consecutive", type=int, default=2)
    p.add_argument("--thermal-baseline-frames", type=int, default=20)
    p.add_argument("--thermal-model-enabled", type=int, default=1, help="Run Layer4 thermal detector on capture video")
    p.add_argument("--thermal-model-id", default=ThermalThreatDetector.DEFAULT_MODEL_ID)
    p.add_argument("--thermal-model-device", type=int, default=-1, help="-1 CPU, >=0 CUDA device index")
    p.add_argument("--thermal-model-threshold", type=float, default=0.25)
    p.add_argument("--thermal-model-every-n", type=int, default=5, help="Run thermal model every N frames")
    p.add_argument("--thermal-suspicious-th", type=float, default=0.25)
    p.add_argument("--thermal-armed-th", type=float, default=0.55)
    p.add_argument("--thermal-min-confidence", type=float, default=0.20)
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

    counts: dict[int, int] = {}
    for lab in labels:
        counts[lab] = counts.get(lab, 0) + 1
    valid = [c for c in counts.values() if c >= int(min_cluster_points)]
    return len(valid)


def _extract_thermal_model_scores(
    frames: list[dict[str, Any]],
    video_path: str,
    args: argparse.Namespace,
) -> tuple[list[float], list[str], list[float], int, str]:
    n = len(frames)
    scores = [0.0] * n
    labels = ["unarmed"] * n
    confs = [0.0] * n

    if int(args.thermal_model_enabled) == 0:
        return scores, labels, confs, 0, ""
    if not video_path:
        return scores, labels, confs, 0, "thermal model skipped: capture video path missing"

    vpath = Path(video_path).expanduser()
    if not vpath.is_file():
        return scores, labels, confs, 0, f"thermal model skipped: video not found ({vpath})"

    try:
        detector = ThermalThreatDetector(
            model_id=str(args.thermal_model_id),
            threshold=float(args.thermal_model_threshold),
            device=int(args.thermal_model_device),
        )
        engine = InferenceEngine(detector=detector)
        scorer = AnomalyScorer(
            suspicious_threshold=float(args.thermal_suspicious_th),
            armed_threshold=float(args.thermal_armed_th),
            min_confidence=float(args.thermal_min_confidence),
        )
    except Exception as exc:
        return scores, labels, confs, 0, f"thermal model init failed: {exc}"

    cap = cv2.VideoCapture(str(vpath))
    if not cap.isOpened():
        return scores, labels, confs, 0, f"thermal model skipped: cannot open video ({vpath})"

    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total_video_frames <= 0:
        cap.release()
        return scores, labels, confs, 0, "thermal model skipped: video has no frames"

    every_n = max(1, int(args.thermal_model_every_n))
    sampled_idxs = list(range(0, n, every_n))
    sampled_set = set(sampled_idxs)
    sampled_count = 0

    for i in sampled_idxs:
        if n <= 1:
            v_idx = 0
        else:
            v_idx = int(round(i * (total_video_frames - 1) / (n - 1)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, float(v_idx))
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        try:
            ir = engine.infer(frame_number=i, timestamp_ms=float(frames[i].get("timestamp_ms", 0.0)), thermal_frame_bgr=frame)
            dec = scorer.evaluate(ir)
            scores[i] = float(dec.anomaly_score)
            labels[i] = str(dec.label)
            confs[i] = float(dec.confidence)
            sampled_count += 1
        except Exception:
            continue

    cap.release()

    last_score = 0.0
    last_label = "unarmed"
    last_conf = 0.0
    for i in range(n):
        if i in sampled_set and confs[i] > 0.0:
            last_score, last_label, last_conf = scores[i], labels[i], confs[i]
        else:
            scores[i], labels[i], confs[i] = last_score, last_label, last_conf

    warning = ""
    if sampled_count == 0:
        warning = "thermal model enabled but produced no sampled detections"
    return scores, labels, confs, sampled_count, warning


def _fusion_verdict(
    *,
    status: str,
    alert_segments: list[dict[str, Any]],
    thermal_model_labels: list[str],
) -> dict[str, Any]:
    """Combine mmWave-driven alert segments with Layer-4 labels into one public verdict."""
    if status != "ALERT" or not alert_segments:
        return {
            "overall": "no_threat",
            "layer4_at_peak": "no_threat",
            "notes": "No fused alert segment met mmWave + thermal support rules.",
        }
    peak_l4: list[str] = []
    for seg in alert_segments:
        pf = int(seg["peak_frame"])
        if 0 <= pf < len(thermal_model_labels):
            peak_l4.append(str(thermal_model_labels[pf]))
    if any(l == "armed" for l in peak_l4):
        overall = "threat"
    elif any(l == "suspicious" for l in peak_l4):
        overall = "suspicious"
    else:
        overall = "suspicious"
    best_l4 = "armed" if any(l == "armed" for l in peak_l4) else ("suspicious" if any(l == "suspicious" for l in peak_l4) else "unarmed")
    return {
        "overall": overall,
        "layer4_at_peak": _l4_label_to_public(best_l4),
        "peak_frame_layer4_labels": peak_l4,
        "label_map": {"armed": "threat", "suspicious": "suspicious", "unarmed": "no_threat"},
    }


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

    video_path = args.video.strip() or (payload.get("capture_info") or {}).get("video", "")
    thermal_model_scores, thermal_model_labels, thermal_model_conf, sampled_count, thermal_model_warning = (
        _extract_thermal_model_scores(frames, video_path, args)
    )

    mm_risks: list[float] = []
    frame_scores: list[float] = []
    mm_candidates: list[bool] = []
    thermal_supported: list[bool] = []
    thermal_model_supported: list[bool] = []
    frame_cluster_counts: list[int] = []

    for i, f in enumerate(frames):
        mm = _mmwave_risk(f)
        mm_points = ((f.get("mmwave") or {}).get("points") or [])
        prs = _presence_raw(f)
        t_delta = max(0.0, _thermal_mean(f) - thermal_baseline)
        tm_score = _clamp01(thermal_model_scores[i] if i < len(thermal_model_scores) else 0.0)
        tm_label = thermal_model_labels[i] if i < len(thermal_model_labels) else "unarmed"
        prs_norm = _clamp01(prs / max(args.presence_th, 1e-6))
        t_norm = _clamp01(t_delta / max(args.thermal_delta_th, 1e-6))
        score = _clamp01(0.60 * mm + 0.15 * prs_norm + 0.10 * t_norm + 0.15 * tm_score)

        mm_risks.append(mm)
        frame_scores.append(score)
        mm_candidates.append(mm >= float(args.mmwave_risk_th))
        thermal_model_supported.append(tm_label in {"suspicious", "armed"})
        if isinstance(mm_points, list):
            frame_cluster_counts.append(_cluster_count(mm_points))
        else:
            frame_cluster_counts.append(0)

    win = max(1, int(args.thermal_support_window))
    t_support_th = float(args.thermal_support_delta_th)
    for i in range(len(frames)):
        left = max(0, i - win + 1)
        tmax = max(max(0.0, thermal_vals[k] - thermal_baseline) for k in range(left, i + 1))
        thermal_supported.append(tmax >= t_support_th)

    suspicious = [
        mm_candidates[i] and (thermal_supported[i] or thermal_model_supported[i]) for i in range(len(frames))
    ]
    segs = _segments_from_flags(suspicious, frame_scores, mm_risks)
    min_consecutive = max(1, int(args.min_consecutive))
    alert_segments = [s for s in segs if int(s["length"]) >= min_consecutive]

    max_consecutive = max((int(s["length"]) for s in segs), default=0)

    nonzero_clusters = [c for c in frame_cluster_counts if c > 0]
    persons_estimated = int(round(max(nonzero_clusters) if nonzero_clusters else 0))
    weapons_suspected = min(persons_estimated, len(alert_segments))

    status = "ALERT" if alert_segments else "NO_ALERT"
    fusion_verdict = _fusion_verdict(
        status=status,
        alert_segments=alert_segments,
        thermal_model_labels=thermal_model_labels,
    )

    report = {
        "status": status,
        "fusion_verdict": fusion_verdict,
        "summary": {
            "frames": len(frames),
            "alerts": len(alert_segments),
            "avg_frame_score": sum(frame_scores) / len(frame_scores),
            "thermal_baseline": thermal_baseline,
            "mmwave_candidate_frames": sum(1 for v in mm_candidates if v),
            "thermal_supported_frames": sum(1 for v in thermal_supported if v),
            "thermal_model_supported_frames": sum(1 for v in thermal_model_supported if v),
            "thermal_model_sampled_frames": int(sampled_count),
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
            "thermal_model_enabled": int(args.thermal_model_enabled),
            "thermal_model_id": str(args.thermal_model_id),
            "thermal_model_device": int(args.thermal_model_device),
            "thermal_model_threshold": float(args.thermal_model_threshold),
            "thermal_model_every_n": int(args.thermal_model_every_n),
            "thermal_suspicious_th": float(args.thermal_suspicious_th),
            "thermal_armed_th": float(args.thermal_armed_th),
            "thermal_min_confidence": float(args.thermal_min_confidence),
        },
        "capture_paths": {
            "capture_json": str(capture_path),
            "video": video_path,
            "risk_config": ((payload.get("capture_info") or {}).get("risk_params") or {}).get("config_path", ""),
        },
        "thermal_model": {
            "warning": thermal_model_warning,
            "frame_decisions_preview": [
                {
                    "frame": i,
                    "label": thermal_model_labels[i],
                    "public_label": _l4_label_to_public(thermal_model_labels[i]),
                    "score": thermal_model_scores[i],
                    "confidence": thermal_model_conf[i],
                }
                for i in range(0, len(frames), max(1, int(args.thermal_model_every_n)))
            ][:40],
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
    print(
        f"status={report['status']} fusion_overall={fusion_verdict['overall']} "
        f"alerts={report['summary']['alerts']} avg_score={report['summary']['avg_frame_score']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
