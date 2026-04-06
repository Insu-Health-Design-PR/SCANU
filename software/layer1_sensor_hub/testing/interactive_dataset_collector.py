#!/usr/bin/env python3
"""Interactive dataset collection menu for safe/unsafe scenarios.

This tool captures rich multisensor data and builds anomaly reports automatically.
It is designed for repeated operator-driven runs with minimal manual file handling.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]

RICH_CAPTURE_SCRIPT = REPO_ROOT / "software/layer1_sensor_hub/testing/capture_all_sensors_rich.py"
ANOMALY_REPORT_SCRIPT = REPO_ROOT / "software/layer1_sensor_hub/testing/view/anomaly_report_from_capture.py"

DEFAULT_CONFIG = REPO_ROOT / "software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_sensitivity.cfg"
DEFAULT_RISK_CONFIG = REPO_ROOT / "software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json"
DEFAULT_OUT_BASE = Path("/home/insu/Desktop/collecting_data")

SAFE_SCENARIOS = [
    "empty_room",
    "person_unarmed",
    "metal_clutter_non_threat",
]

UNSAFE_SCENARIOS = [
    "armed_on_body",
    "concealed_object",
    "threat_in_bag",
]


@dataclass
class Case:
    label_class: str
    scenario: str
    distance_ft: str
    run_num: int


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Interactive dataset collector (safe/unsafe)")
    p.add_argument("--config", default=str(DEFAULT_CONFIG), help="mmWave cfg path")
    p.add_argument("--risk-config", default=str(DEFAULT_RISK_CONFIG), help="risk JSON path")
    p.add_argument("--out-base", default=str(DEFAULT_OUT_BASE), help="Base output directory")

    p.add_argument("--frames", type=int, default=350)
    p.add_argument("--interval-s", type=float, default=0.1)
    p.add_argument("--mmwave-timeout-ms", type=int, default=200)

    p.add_argument("--presence", choices=("ifx", "mock", "off"), default="ifx")
    p.add_argument("--ifx-uuid", default=None)
    p.add_argument("--thermal-device", type=int, default=0)
    p.add_argument("--thermal-width", type=int, default=640)
    p.add_argument("--thermal-height", type=int, default=480)
    p.add_argument("--thermal-fps", type=int, default=30)

    p.add_argument("--cli-port", default=None)
    p.add_argument("--data-port", default=None)
    p.add_argument("--skip-mmwave-config", action="store_true")

    # Report thresholds (sensitive defaults for training collection)
    p.add_argument("--mmwave-risk-th", type=float, default=0.03)
    p.add_argument("--presence-th", type=float, default=1.0)
    p.add_argument("--thermal-delta-th", type=float, default=3.0)
    p.add_argument("--fusion-mode", default="mm_primary_temporal")
    p.add_argument("--thermal-support-window", type=int, default=10)
    p.add_argument("--thermal-support-delta-th", type=float, default=1.0)
    p.add_argument("--min-consecutive", type=int, default=2)
    p.add_argument("--thermal-baseline-frames", type=int, default=20)
    return p


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
    return s.strip("_") or "na"


def _distance_slug(distance_ft: str) -> str:
    s = _slug(distance_ft).replace("_", "")
    if not s.endswith("ft"):
        s = f"{s}ft"
    return s


def _next_run_number(target_dir: Path, prefix: str) -> int:
    best = 0
    pattern = re.compile(rf"^{re.escape(prefix)}_r(\d{{2}})_")
    for p in target_dir.glob(f"{prefix}_r*_*.json"):
        m = pattern.match(p.stem)
        if m:
            best = max(best, int(m.group(1)))
    return best + 1


def _pick_class() -> str | None:
    while True:
        print("\n=== Main Menu ===")
        print("1) SAFE")
        print("2) UNSAFE")
        print("3) EXIT")
        c = input("Choose option: ").strip().lower()
        if c in ("1", "safe"):
            return "safe"
        if c in ("2", "unsafe"):
            return "unsafe"
        if c in ("3", "exit", "q", "quit"):
            return None
        print("Invalid option. Try again.")


def _pick_scenario(label_class: str) -> str:
    options = SAFE_SCENARIOS if label_class == "safe" else UNSAFE_SCENARIOS
    while True:
        print(f"\n=== Scenario ({label_class.upper()}) ===")
        for i, name in enumerate(options, start=1):
            print(f"{i}) {name}")
        raw = input("Choose scenario: ").strip().lower()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        if raw in options:
            return raw
        print("Invalid scenario. Try again.")


def _capture_case(args: argparse.Namespace, case: Case, out_base: Path) -> dict:
    scenario_dir = out_base / case.label_class / case.scenario
    scenario_dir.mkdir(parents=True, exist_ok=True)

    dist_slug = _distance_slug(case.distance_ft)
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    base_id = f"{case.label_class}_{case.scenario}_{dist_slug}_r{case.run_num:02d}_{ts}"

    video_path = scenario_dir / f"{base_id}.mp4"
    capture_path = scenario_dir / f"{base_id}_capture.json"
    report_path = scenario_dir / f"{base_id}_report.json"

    capture_cmd = [
        sys.executable,
        str(RICH_CAPTURE_SCRIPT),
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
        "--video",
        str(video_path),
        "--output",
        str(capture_path),
    ]
    if args.ifx_uuid:
        capture_cmd += ["--ifx-uuid", str(args.ifx_uuid)]
    if args.cli_port:
        capture_cmd += ["--cli-port", str(args.cli_port)]
    if args.data_port:
        capture_cmd += ["--data-port", str(args.data_port)]
    if args.skip_mmwave_config:
        capture_cmd += ["--skip-mmwave-config"]

    print("\n[CAPTURING]")
    print(" ".join(capture_cmd))
    subprocess.run(capture_cmd, check=True)

    report_cmd = [
        sys.executable,
        str(ANOMALY_REPORT_SCRIPT),
        "--capture-json",
        str(capture_path),
        "--output",
        str(report_path),
        "--mmwave-risk-th",
        str(args.mmwave_risk_th),
        "--presence-th",
        str(args.presence_th),
        "--thermal-delta-th",
        str(args.thermal_delta_th),
        "--fusion-mode",
        str(args.fusion_mode),
        "--thermal-support-window",
        str(args.thermal_support_window),
        "--thermal-support-delta-th",
        str(args.thermal_support_delta_th),
        "--min-consecutive",
        str(args.min_consecutive),
        "--thermal-baseline-frames",
        str(args.thermal_baseline_frames),
    ]
    print("\n[ANALYZING]")
    print(" ".join(report_cmd))
    subprocess.run(report_cmd, check=True)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    return {
        "timestamp": datetime.now().isoformat(),
        "label_class": case.label_class,
        "scenario": case.scenario,
        "distance_ft": case.distance_ft,
        "run_num": case.run_num,
        "expected": "NO_ALERT" if case.label_class == "safe" else "ALERT",
        "result_status": report.get("status"),
        "alerts": int((report.get("summary") or {}).get("alerts", 0)),
        "avg_frame_score": float((report.get("summary") or {}).get("avg_frame_score", 0.0)),
        "video": str(video_path),
        "capture_json": str(capture_path),
        "report_json": str(report_path),
    }


def _append_manifest(out_base: Path, row: dict) -> None:
    manifest = out_base / "manifest.jsonl"
    with manifest.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=True) + "\n")


def _print_result(row: dict) -> None:
    print("\n[DONE]")
    print(f"class={row['label_class']} scenario={row['scenario']} distance={row['distance_ft']} run={row['run_num']:02d}")
    print(f"status={row['result_status']} alerts={row['alerts']} avg_score={row['avg_frame_score']:.4f}")
    print(f"capture={row['capture_json']}")
    print(f"report={row['report_json']}")
    print(f"video={row['video']}")


def _post_action() -> str:
    print("\nAction: Enter=next | r=repeat last | m=main menu | exit=quit")
    return input("> ").strip().lower()


def main() -> int:
    args = build_parser().parse_args()
    out_base = Path(args.out_base).expanduser().resolve()
    out_base.mkdir(parents=True, exist_ok=True)
    (out_base / "safe").mkdir(parents=True, exist_ok=True)
    (out_base / "unsafe").mkdir(parents=True, exist_ok=True)

    print("Interactive Dataset Collector")
    print(f"Output base: {out_base}")
    print("Folders: safe/ and unsafe/")
    print("Type 'exit' anytime in menu/action to stop.")

    last_case: Case | None = None
    next_case: Case | None = None

    while True:
        try:
            if next_case is None:
                label_class = _pick_class()
                if label_class is None:
                    print("Exit requested.")
                    return 0
                scenario = _pick_scenario(label_class)
                distance_ft = input("Distance in ft (example: 5, 10, 12.5): ").strip()
                if distance_ft.lower() in ("exit", "quit", "q"):
                    print("Exit requested.")
                    return 0
                if not distance_ft:
                    distance_ft = "na"
                target_dir = out_base / label_class / scenario
                prefix = f"{label_class}_{scenario}_{_distance_slug(distance_ft)}"
                run_num = _next_run_number(target_dir, prefix)
                next_case = Case(
                    label_class=label_class,
                    scenario=scenario,
                    distance_ft=distance_ft,
                    run_num=run_num,
                )

            print("\n[PREPARE]")
            print(
                f"class={next_case.label_class} scenario={next_case.scenario} "
                f"distance={next_case.distance_ft}ft run={next_case.run_num:02d}"
            )
            prompt = input("Press Enter to start capture, or type 'exit': ").strip().lower()
            if prompt in ("exit", "quit", "q"):
                print("Exit requested.")
                return 0

            row = _capture_case(args, next_case, out_base)
            _append_manifest(out_base, row)
            _print_result(row)
            last_case = next_case

            action = _post_action()
            if action in ("exit", "quit", "q"):
                print("Exit requested.")
                return 0
            if action == "r":
                if last_case is None:
                    next_case = None
                    continue
                target_dir = out_base / last_case.label_class / last_case.scenario
                prefix = f"{last_case.label_class}_{last_case.scenario}_{_distance_slug(last_case.distance_ft)}"
                run_num = _next_run_number(target_dir, prefix)
                next_case = Case(
                    label_class=last_case.label_class,
                    scenario=last_case.scenario,
                    distance_ft=last_case.distance_ft,
                    run_num=run_num,
                )
                continue
            if action == "m":
                next_case = None
                continue

            # Default: same class/scenario/distance, next run number.
            if last_case is not None:
                target_dir = out_base / last_case.label_class / last_case.scenario
                prefix = f"{last_case.label_class}_{last_case.scenario}_{_distance_slug(last_case.distance_ft)}"
                run_num = _next_run_number(target_dir, prefix)
                next_case = Case(
                    label_class=last_case.label_class,
                    scenario=last_case.scenario,
                    distance_ft=last_case.distance_ft,
                    run_num=run_num,
                )
            else:
                next_case = None

        except KeyboardInterrupt:
            print("\nInterrupted by user. Exiting.")
            return 0
        except Exception as exc:
            print(f"\n[ERROR] {exc}")
            print("Action: m=main menu | r=repeat last | exit=quit")
            action = input("> ").strip().lower()
            if action in ("exit", "quit", "q"):
                return 1
            if action == "r" and last_case is not None:
                target_dir = out_base / last_case.label_class / last_case.scenario
                prefix = f"{last_case.label_class}_{last_case.scenario}_{_distance_slug(last_case.distance_ft)}"
                run_num = _next_run_number(target_dir, prefix)
                next_case = Case(
                    label_class=last_case.label_class,
                    scenario=last_case.scenario,
                    distance_ft=last_case.distance_ft,
                    run_num=run_num,
                )
            else:
                next_case = None


if __name__ == "__main__":
    raise SystemExit(main())

