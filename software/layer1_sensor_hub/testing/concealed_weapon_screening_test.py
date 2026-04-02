#!/usr/bin/env python3
"""Run a live concealed-object screening test with camera + radar + Infineon.

This script executes `capture_all_sensors_rich.py` and then analyzes its JSON output
for suspicious windows using a simple heuristic fusion.

Important: this is an experimental screening tool, not a certified detector.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RICH_CAPTURE_SCRIPT = REPO_ROOT / "software/layer1_sensor_hub/testing/capture_all_sensors_rich.py"
DEFAULT_RISK_CONFIG = REPO_ROOT / "software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json"
DEFAULT_OUT_DIR = REPO_ROOT / "software/layer1_sensor_hub/testing/view"


@dataclass
class Segment:
    start_index: int
    end_index: int
    length_frames: int
    max_mmwave_risk: float
    max_presence: float
    max_thermal_delta: float


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Live concealed-object screening test")

    p.add_argument("--config", required=True, help="Path to mmWave cfg")
    p.add_argument("--frames", type=int, default=300, help="Capture frames")
    p.add_argument("--interval-s", type=float, default=0.1, help="Capture interval")
    p.add_argument("--mmwave-timeout-ms", type=int, default=200)

    p.add_argument("--cli-port", default=None)
    p.add_argument("--data-port", default=None)
    p.add_argument("--skip-mmwave-config", action="store_true")

    p.add_argument("--ifx-uuid", default=None)
    p.add_argument("--presence", choices=("ifx", "mock", "off"), default="ifx")

    p.add_argument("--thermal-device", type=int, default=0)
    p.add_argument("--thermal-width", type=int, default=640)
    p.add_argument("--thermal-height", type=int, default=480)
    p.add_argument("--thermal-fps", type=int, default=30)

    p.add_argument("--risk-config", default=str(DEFAULT_RISK_CONFIG), help="Risk config JSON")

    p.add_argument("--mmwave-risk-th", type=float, default=0.45, help="Threshold for mmWave risk")
    p.add_argument("--presence-th", type=float, default=0.55, help="Threshold for presence")
    p.add_argument("--thermal-delta-th", type=float, default=6.0, help="Threshold above thermal baseline")
    p.add_argument("--thermal-baseline-frames", type=int, default=20, help="Frames used to estimate thermal baseline")
    p.add_argument("--min-consecutive", type=int, default=6, help="Min consecutive suspicious frames")

    p.add_argument(
        "--video",
        default=str(DEFAULT_OUT_DIR / "concealed_screening.mp4"),
        help="Output video path",
    )
    p.add_argument(
        "--capture-json",
        default=str(DEFAULT_OUT_DIR / "concealed_screening_capture.json"),
        help="Raw capture JSON path",
    )
    p.add_argument(
        "--report-json",
        default=str(DEFAULT_OUT_DIR / "concealed_screening_report.json"),
        help="Report JSON path",
    )
    p.add_argument("--fail-on-alert", action="store_true", help="Exit non-zero if suspicious segment is found")
    return p


def _run_capture(args: argparse.Namespace) -> None:
    cmd = [
        sys.executable,
        str(RICH_CAPTURE_SCRIPT),
        "--config",
        str(args.config),
        "--frames",
        str(args.frames),
        "--interval-s",
        str(args.interval_s),
        "--mmwave-timeout-ms",
        str(args.mmwave_timeout_ms),
        "--presence",
        str(args.presence),
        "--thermal-device",
        str(args.thermal_device),
        "--thermal-width",
        str(args.thermal_width),
        "--thermal-height",
        str(args.thermal_height),
        "--thermal-fps",
        str(args.thermal_fps),
        "--risk-config",
        str(args.risk_config),
        "--video",
        str(args.video),
        "--output",
        str(args.capture_json),
    ]

    if args.cli_port:
        cmd += ["--cli-port", str(args.cli_port)]
    if args.data_port:
        cmd += ["--data-port", str(args.data_port)]
    if args.skip_mmwave_config:
        cmd += ["--skip-mmwave-config"]
    if args.ifx_uuid:
        cmd += ["--ifx-uuid", str(args.ifx_uuid)]

    print("Running live capture:")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def _safe_float(v: object, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _collect_segments(flags: list[bool], mmrisk: list[float], presence: list[float], thermal_delta: list[float], min_len: int) -> list[Segment]:
    segments: list[Segment] = []
    start: int | None = None

    def close_segment(end_idx: int) -> None:
        nonlocal start
        if start is None:
            return
        length = end_idx - start + 1
        if length >= min_len:
            seg = Segment(
                start_index=start,
                end_index=end_idx,
                length_frames=length,
                max_mmwave_risk=max(mmrisk[start : end_idx + 1]),
                max_presence=max(presence[start : end_idx + 1]),
                max_thermal_delta=max(thermal_delta[start : end_idx + 1]),
            )
            segments.append(seg)
        start = None

    for i, flag in enumerate(flags):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            close_segment(i - 1)

    if start is not None:
        close_segment(len(flags) - 1)

    return segments


def _analyze_capture(args: argparse.Namespace) -> dict:
    capture_path = Path(args.capture_json).expanduser().resolve()
    payload = json.loads(capture_path.read_text(encoding="utf-8"))
    frames = payload.get("frames", [])
    if not frames:
        raise RuntimeError(f"No frames found in capture JSON: {capture_path}")

    thermal_values = [_safe_float((f.get("thermal") or {}).get("mean_u8"), 0.0) for f in frames]
    baseline_n = max(1, min(int(args.thermal_baseline_frames), len(thermal_values)))
    thermal_baseline = sum(thermal_values[:baseline_n]) / baseline_n

    mmrisk_values = [_safe_float((((f.get("mmwave") or {}).get("risk_features") or {}).get("risk_score_mmwave")), 0.0) for f in frames]
    presence_values = [_safe_float(((f.get("presence") or {}).get("presence_raw")), 0.0) for f in frames]
    thermal_delta_values = [v - thermal_baseline for v in thermal_values]

    suspicious_flags: list[bool] = []
    per_frame_score: list[float] = []
    for mr, pr, td in zip(mmrisk_values, presence_values, thermal_delta_values):
        score = 0.60 * mr + 0.25 * min(1.0, max(0.0, pr)) + 0.15 * min(1.0, max(0.0, td / max(1e-6, args.thermal_delta_th)))
        per_frame_score.append(score)
        suspicious = mr >= args.mmwave_risk_th and (pr >= args.presence_th or td >= args.thermal_delta_th)
        suspicious_flags.append(bool(suspicious))

    segments = _collect_segments(
        suspicious_flags,
        mmrisk_values,
        presence_values,
        thermal_delta_values,
        min_len=max(1, int(args.min_consecutive)),
    )

    avg_score = sum(per_frame_score) / max(1, len(per_frame_score))
    report = {
        "status": "ALERT" if segments else "NO_ALERT",
        "summary": {
            "frames": len(frames),
            "alerts": len(segments),
            "avg_frame_score": avg_score,
            "thermal_baseline": thermal_baseline,
        },
        "thresholds": {
            "mmwave_risk_th": float(args.mmwave_risk_th),
            "presence_th": float(args.presence_th),
            "thermal_delta_th": float(args.thermal_delta_th),
            "min_consecutive": int(args.min_consecutive),
            "thermal_baseline_frames": int(args.thermal_baseline_frames),
        },
        "capture_paths": {
            "capture_json": str(Path(args.capture_json).resolve()),
            "video": str(Path(args.video).resolve()),
            "risk_config": str(Path(args.risk_config).resolve()),
        },
        "segments": [
            {
                "start_index": s.start_index,
                "end_index": s.end_index,
                "length_frames": s.length_frames,
                "max_mmwave_risk": s.max_mmwave_risk,
                "max_presence": s.max_presence,
                "max_thermal_delta": s.max_thermal_delta,
            }
            for s in segments
        ],
    }
    return report


def main() -> int:
    args = build_parser().parse_args()

    capture_json_path = Path(args.capture_json).expanduser().resolve()
    capture_json_path.parent.mkdir(parents=True, exist_ok=True)
    Path(args.video).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    Path(args.report_json).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    _run_capture(args)
    report = _analyze_capture(args)

    out_report = Path(args.report_json).expanduser().resolve()
    out_report.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=" * 80)
    print(f"Screening status: {report['status']}")
    print(f"Alerts found   : {report['summary']['alerts']}")
    print(f"Capture JSON   : {Path(args.capture_json).resolve()}")
    print(f"Report JSON    : {out_report}")
    print("=" * 80)

    if args.fail_on_alert and report["status"] == "ALERT":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
