#!/usr/bin/env python3
"""Run multi-scenario distance validation campaign for concealed-object screening.

This orchestrator runs `concealed_weapon_screening_test.py` repeatedly using an
operator-guided plan (scenario + distance) and stores artifacts for each run:
- video (.mp4)
- raw capture (.json)
- analysis report (.json)

Important: this is an experimental workflow, not a certified detector.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCREENING_SCRIPT = REPO_ROOT / "software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py"
DEFAULT_CFG = REPO_ROOT / "software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_v2.cfg"
DEFAULT_RISK = REPO_ROOT / "software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json"
DEFAULT_PLAN = REPO_ROOT / "software/layer1_sensor_hub/testing/configs/weapon_distance_campaign_plan.json"
DEFAULT_OUT = REPO_ROOT / "software/layer1_sensor_hub/testing/view/weapon_distance_campaign"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Distance validation campaign for concealed-object screening")
    p.add_argument("--plan", default=str(DEFAULT_PLAN), help="Campaign plan JSON path")
    p.add_argument("--campaign-name", default=None, help="Output folder name. Default: timestamp.")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT), help="Base output directory")
    p.add_argument("--repeats", type=int, default=1, help="How many repeats per scenario-distance")
    p.add_argument("--no-prompt", action="store_true", help="Run all cases without waiting for Enter")

    p.add_argument("--mode", choices=("default", "no_ifx"), default="no_ifx")
    p.add_argument("--config", default=str(DEFAULT_CFG), help="mmWave cfg path")
    p.add_argument("--risk-config", default=str(DEFAULT_RISK), help="risk JSON path")
    p.add_argument("--frames", type=int, default=350)
    p.add_argument("--interval-s", type=float, default=0.1)
    p.add_argument("--mmwave-timeout-ms", type=int, default=200)
    p.add_argument("--thermal-device", type=int, default=0)
    p.add_argument("--cli-port", default=None)
    p.add_argument("--data-port", default=None)
    p.add_argument("--skip-mmwave-config", action="store_true")

    p.add_argument("--mmwave-risk-th", type=float, default=0.06)
    p.add_argument("--presence-th", type=float, default=1.0)
    p.add_argument("--thermal-delta-th", type=float, default=3.5)
    p.add_argument("--min-consecutive", type=int, default=3)
    p.add_argument(
        "--fusion-mode",
        choices=("strict_and", "mm_primary_temporal", "mm_primary_score_boost"),
        default="mm_primary_temporal",
    )
    p.add_argument("--thermal-support-window", type=int, default=12)
    p.add_argument("--thermal-support-delta-th", type=float, default=None)
    return p


def _slug(s: str) -> str:
    out = []
    for ch in s.lower().strip():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("_")
    while "__" in "".join(out):
        out = list("".join(out).replace("__", "_"))
    return "".join(out).strip("_") or "scenario"


def _load_plan(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise RuntimeError(f"Invalid plan JSON (missing scenarios list): {path}")
    return scenarios


def _expected_from_label(v: str) -> str:
    normalized = str(v).strip().lower()
    if normalized in ("threat_detected", "threat", "alert"):
        return "THREAT_DETECTED"
    if normalized in ("motion_trigger", "trigger_only", "n_a", "na"):
        return "TRIGGER_ONLY"
    return "NO_THREAT"


def _evaluate(expected: str, status: str) -> tuple[str, str]:
    if expected == "TRIGGER_ONLY":
        return ("N/A", "Motion-trigger validation; manual review required.")
    if expected == "THREAT_DETECTED":
        return ("PASS" if status == "ALERT" else "FAIL", "Expected ALERT.")
    return ("PASS" if status == "NO_ALERT" else "FAIL", "Expected NO_ALERT.")


def _run_case(args: argparse.Namespace, out_dir: Path, case_id: str) -> None:
    video = out_dir / f"{case_id}.mp4"
    capture_json = out_dir / f"{case_id}_capture.json"
    report_json = out_dir / f"{case_id}_report.json"

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
        "--mmwave-risk-th",
        str(args.mmwave_risk_th),
        "--presence-th",
        str(args.presence_th),
        "--thermal-delta-th",
        str(args.thermal_delta_th),
        "--min-consecutive",
        str(args.min_consecutive),
        "--fusion-mode",
        str(args.fusion_mode),
        "--thermal-support-window",
        str(args.thermal_support_window),
        "--video",
        str(video),
        "--capture-json",
        str(capture_json),
        "--report-json",
        str(report_json),
    ]
    if args.thermal_support_delta_th is not None:
        cmd += ["--thermal-support-delta-th", str(args.thermal_support_delta_th)]
    if args.cli_port:
        cmd += ["--cli-port", str(args.cli_port)]
    if args.data_port:
        cmd += ["--data-port", str(args.data_port)]
    if args.skip_mmwave_config:
        cmd += ["--skip-mmwave-config"]

    print("\n" + "=" * 100)
    print(f"Running case: {case_id}")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    args = build_parser().parse_args()
    plan_path = Path(args.plan).expanduser().resolve()
    scenarios = _load_plan(plan_path)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    campaign_name = args.campaign_name or f"campaign_{stamp}"
    campaign_dir = Path(args.out_dir).expanduser().resolve() / campaign_name
    campaign_dir.mkdir(parents=True, exist_ok=True)

    print("Distance validation campaign")
    print(f"Plan: {plan_path}")
    print(f"Output dir: {campaign_dir}")
    print(f"Mode: {args.mode}")
    print(f"Config: {Path(args.config).expanduser().resolve()}")
    print(f"Risk config: {Path(args.risk_config).expanduser().resolve()}")

    rows: list[dict] = []
    case_idx = 0
    for scenario in scenarios:
        scenario_id = _slug(str(scenario.get("id") or scenario.get("name") or "scenario"))
        scenario_label = str(scenario.get("name") or scenario_id)
        notes = str(scenario.get("notes") or "")
        expected = _expected_from_label(str(scenario.get("expected") or ""))

        distances = scenario.get("distances_ft")
        if not isinstance(distances, list) or len(distances) == 0:
            distances = [None]

        for d in distances:
            for rep in range(1, max(1, int(args.repeats)) + 1):
                case_idx += 1
                dist_label = f"{int(d)}ft" if d is not None else "na"
                case_id = f"{case_idx:03d}_{scenario_id}_{dist_label}_r{rep}"

                if not args.no_prompt:
                    print("\n" + "-" * 100)
                    print(f"Prepare case {case_idx}: {scenario_label}")
                    print(f"Distance: {dist_label}")
                    print(f"Expected: {expected}")
                    if notes:
                        print(f"Notes: {notes}")
                    input("Press Enter to start this case...")

                _run_case(args, campaign_dir, case_id)

                report_path = campaign_dir / f"{case_id}_report.json"
                report = json.loads(report_path.read_text(encoding="utf-8"))
                status = str(report.get("status") or "UNKNOWN")
                alerts = int((report.get("summary") or {}).get("alerts", 0))
                avg_score = float((report.get("summary") or {}).get("avg_frame_score", 0.0))
                decision, rule = _evaluate(expected, status)

                rows.append(
                    {
                        "case_id": case_id,
                        "scenario": scenario_label,
                        "distance_ft": "" if d is None else int(d),
                        "expected": expected,
                        "status": status,
                        "alerts": alerts,
                        "avg_frame_score": avg_score,
                        "decision": decision,
                        "rule": rule,
                        "notes": notes,
                        "video": str((campaign_dir / f"{case_id}.mp4").resolve()),
                        "capture_json": str((campaign_dir / f"{case_id}_capture.json").resolve()),
                        "report_json": str(report_path.resolve()),
                    }
                )

    summary_json = campaign_dir / "campaign_results.json"
    summary_csv = campaign_dir / "campaign_results.csv"
    summary_md = campaign_dir / "campaign_summary.md"

    summary_payload = {
        "meta": {
            "campaign_name": campaign_name,
            "plan": str(plan_path),
            "mode": args.mode,
            "config": str(Path(args.config).expanduser().resolve()),
            "risk_config": str(Path(args.risk_config).expanduser().resolve()),
            "frames": int(args.frames),
            "interval_s": float(args.interval_s),
            "fusion_mode": str(args.fusion_mode),
            "thermal_support_window": int(args.thermal_support_window),
            "thresholds": {
                "mmwave_risk_th": float(args.mmwave_risk_th),
                "presence_th": float(args.presence_th),
                "thermal_delta_th": float(args.thermal_delta_th),
                "min_consecutive": int(args.min_consecutive),
                "thermal_support_delta_th": args.thermal_support_delta_th,
            },
            "repeats": int(args.repeats),
            "generated_at": datetime.now().isoformat(),
        },
        "results": rows,
    }
    summary_json.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case_id",
                "scenario",
                "distance_ft",
                "expected",
                "status",
                "alerts",
                "avg_frame_score",
                "decision",
                "rule",
                "notes",
                "video",
                "capture_json",
                "report_json",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    lines = [
        f"# Distance Campaign Summary: {campaign_name}",
        "",
        f"- Total cases: {len(rows)}",
        f"- Output: `{campaign_dir}`",
        "",
        "| Case | Scenario | Distance | Expected | Status | Decision |",
        "|---|---|---:|---|---|---|",
    ]
    for r in rows:
        dist = f"{r['distance_ft']}ft" if r["distance_ft"] != "" else "N/A"
        lines.append(
            f"| {r['case_id']} | {r['scenario']} | {dist} | {r['expected']} | {r['status']} | {r['decision']} |"
        )
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n" + "=" * 100)
    print(f"Campaign complete. Cases: {len(rows)}")
    print(f"Summary JSON: {summary_json}")
    print(f"Summary CSV:  {summary_csv}")
    print(f"Summary MD:   {summary_md}")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
