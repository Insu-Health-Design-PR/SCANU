#!/usr/bin/env python3
"""Run 3-scenario screening comparison and generate a combined analysis report.

Scenarios:
1) empty_room
2) person_unarmed
3) person_concealed_object

This script orchestrates repeated runs of concealed_weapon_screening_test.py and
summarizes separation quality between scenarios.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCREENING_SCRIPT = REPO_ROOT / "software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py"
DEFAULT_CFG = REPO_ROOT / "software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_sensitivity.cfg"
DEFAULT_RISK = REPO_ROOT / "software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json"
DEFAULT_OUT = REPO_ROOT / "software/layer1_sensor_hub/testing/view"
SCENARIOS = ["empty_room", "person_unarmed", "person_concealed_object"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="3-scenario comparison test for concealed-object screening")
    p.add_argument("--mode", choices=("default", "no_ifx"), default="no_ifx")
    p.add_argument("--config", default=str(DEFAULT_CFG), help="mmWave cfg path")
    p.add_argument("--risk-config", default=str(DEFAULT_RISK), help="risk JSON path")
    p.add_argument("--frames", type=int, default=350)
    p.add_argument("--interval-s", type=float, default=0.1)
    p.add_argument("--mmwave-timeout-ms", type=int, default=200)
    p.add_argument("--thermal-device", type=int, default=0)
    p.add_argument(
        "--fusion-mode",
        choices=("strict_and", "mm_primary_temporal", "mm_primary_score_boost"),
        default=None,
        help="Optional fusion mode override forwarded to concealed_weapon_screening_test.py",
    )
    p.add_argument(
        "--thermal-support-window",
        type=int,
        default=None,
        help="Optional thermal support window (frames) for temporal fusion mode.",
    )
    p.add_argument(
        "--thermal-support-delta-th",
        type=float,
        default=None,
        help="Optional thermal support threshold override.",
    )

    p.add_argument("--cli-port", default=None)
    p.add_argument("--data-port", default=None)
    p.add_argument("--skip-mmwave-config", action="store_true")

    p.add_argument(
        "--output-prefix",
        default="three_scenario",
        help="Prefix for generated files under testing/view",
    )
    p.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT),
        help="Output directory for scenario files and final comparison report",
    )
    p.add_argument(
        "--no-prompt",
        action="store_true",
        help="Run scenarios without waiting for Enter between stages",
    )
    p.add_argument(
        "--comparison-report",
        default=None,
        help="Optional path for final comparison report JSON",
    )
    return p


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    arr = sorted(values)
    idx = int(max(0, min(len(arr) - 1, round((len(arr) - 1) * p))))
    return float(arr[idx])


def _load_capture_metrics(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    frames = payload.get("frames", [])
    mm_risks = [float((((f.get("mmwave") or {}).get("risk_features") or {}).get("risk_score_mmwave") or 0.0)) for f in frames]
    mm_points = [int(((f.get("mmwave") or {}).get("num_points") or 0)) for f in frames]
    thermal_vals = [float(((f.get("thermal") or {}).get("mean_u8") or 0.0)) for f in frames]

    n = max(1, len(frames))
    return {
        "frames": len(frames),
        "mm_risk_max": max(mm_risks) if mm_risks else 0.0,
        "mm_risk_p95": _percentile(mm_risks, 0.95),
        "mm_risk_mean": (sum(mm_risks) / n) if mm_risks else 0.0,
        "mm_points_nonzero_ratio": (sum(1 for v in mm_points if v > 0) / n),
        "thermal_mean": (sum(thermal_vals) / n) if thermal_vals else 0.0,
    }


def _run_one_scenario(args: argparse.Namespace, scenario: str, out_dir: Path) -> dict:
    prefix = f"{args.output_prefix}_{scenario}"
    video = out_dir / f"{prefix}.mp4"
    capture_json = out_dir / f"{prefix}_capture.json"
    report_json = out_dir / f"{prefix}_report.json"

    cmd = [
        sys.executable,
        str(SCREENING_SCRIPT),
        "--mode",
        str(args.mode),
        "--config",
        str(args.config),
        "--risk-config",
        str(args.risk_config),
        "--frames",
        str(args.frames),
        "--interval-s",
        str(args.interval_s),
        "--mmwave-timeout-ms",
        str(args.mmwave_timeout_ms),
        "--thermal-device",
        str(args.thermal_device),
        "--video",
        str(video),
        "--capture-json",
        str(capture_json),
        "--report-json",
        str(report_json),
    ]
    if args.cli_port:
        cmd += ["--cli-port", str(args.cli_port)]
    if args.data_port:
        cmd += ["--data-port", str(args.data_port)]
    if args.skip_mmwave_config:
        cmd += ["--skip-mmwave-config"]
    if args.fusion_mode is not None:
        cmd += ["--fusion-mode", str(args.fusion_mode)]
    if args.thermal_support_window is not None:
        cmd += ["--thermal-support-window", str(args.thermal_support_window)]
    if args.thermal_support_delta_th is not None:
        cmd += ["--thermal-support-delta-th", str(args.thermal_support_delta_th)]

    print("=" * 90)
    print(f"Running scenario: {scenario}")
    print("Command:")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

    rep = json.loads(report_json.read_text(encoding="utf-8"))
    cap = _load_capture_metrics(capture_json)
    return {
        "scenario": scenario,
        "status": rep.get("status"),
        "alerts": int((rep.get("summary") or {}).get("alerts", 0)),
        "avg_frame_score": float((rep.get("summary") or {}).get("avg_frame_score", 0.0)),
        "capture_metrics": cap,
        "paths": {
            "video": str(video.resolve()),
            "capture_json": str(capture_json.resolve()),
            "report_json": str(report_json.resolve()),
        },
    }


def _compute_comparison(s: dict[str, dict]) -> dict:
    e = s["empty_room"]["capture_metrics"]
    u = s["person_unarmed"]["capture_metrics"]
    a = s["person_concealed_object"]["capture_metrics"]

    delta_unarmed_vs_empty = u["mm_risk_p95"] - e["mm_risk_p95"]
    delta_armed_vs_unarmed = a["mm_risk_p95"] - u["mm_risk_p95"]

    recommended_threshold = None
    if a["mm_risk_p95"] > u["mm_risk_p95"]:
        recommended_threshold = (a["mm_risk_p95"] + u["mm_risk_p95"]) / 2.0

    status = "LOW_SEPARATION"
    if delta_unarmed_vs_empty > 0.01 and delta_armed_vs_unarmed > 0.01:
        status = "GOOD_SEPARATION"
    elif delta_unarmed_vs_empty > 0.005 or delta_armed_vs_unarmed > 0.005:
        status = "PARTIAL_SEPARATION"

    return {
        "status": status,
        "delta_mm_risk_p95": {
            "person_vs_empty": delta_unarmed_vs_empty,
            "armed_vs_person": delta_armed_vs_unarmed,
        },
        "recommended_mmwave_risk_threshold": recommended_threshold,
    }


def main() -> int:
    args = build_parser().parse_args()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Three-scenario comparison test")
    print("Scenarios order:")
    print("1) empty_room")
    print("2) person_unarmed")
    print("3) person_concealed_object")

    results: list[dict] = []
    for i, scenario in enumerate(SCENARIOS, start=1):
        if not args.no_prompt:
            print("\n" + "-" * 90)
            print(f"Prepare scenario {i}/{len(SCENARIOS)}: {scenario}")
            input("Press Enter to start this scenario...")
        results.append(_run_one_scenario(args, scenario, out_dir))

    by_name = {r["scenario"]: r for r in results}
    comparison = _compute_comparison(by_name)

    final = {
        "meta": {
            "mode": args.mode,
            "config": str(Path(args.config).expanduser().resolve()),
            "risk_config": str(Path(args.risk_config).expanduser().resolve()),
            "frames": int(args.frames),
            "interval_s": float(args.interval_s),
        },
        "scenarios": results,
        "comparison": comparison,
    }

    if args.comparison_report:
        out_report = Path(args.comparison_report).expanduser().resolve()
    else:
        out_report = out_dir / f"{args.output_prefix}_comparison_report.json"

    out_report.write_text(json.dumps(final, indent=2), encoding="utf-8")
    print("\n" + "=" * 90)
    print(f"Comparison status: {comparison['status']}")
    print(f"Recommended mmWave threshold: {comparison['recommended_mmwave_risk_threshold']}")
    print(f"Saved comparison report: {out_report}")
    print("=" * 90)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
