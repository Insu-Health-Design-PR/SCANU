#!/usr/bin/env python3
"""Quick hardware visibility check for layer1_sensor_hub."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from software.layer1_sensor_hub.mmwave import SerialManager


def list_serial() -> None:
    ports = SerialManager.list_all_ports()
    print("\n== Serial Ports ==")
    if not ports:
        print("No serial ports found.")
        return
    for p in ports:
        print(f"- {p.get('device')} | {p.get('description')} | manufacturer={p.get('manufacturer')}")


def list_video() -> None:
    print("\n== Video Nodes ==")
    nodes = sorted(Path("/dev").glob("video*"))
    if not nodes:
        print("No /dev/video* nodes found.")
        return
    for n in nodes:
        print(f"- {n}")


def detect_mmwave() -> None:
    print("\n== mmWave Detect ==")
    mgr = SerialManager()
    try:
        ports = mgr.find_radar_ports(verbose=False)
        print(f"Detected: CLI={ports.config_port} DATA={ports.data_port} ({ports.description})")
    except Exception as exc:
        print(f"No mmWave pair detected: {exc}")


def main() -> int:
    p = argparse.ArgumentParser(description="Device checker (serial + video + mmWave)")
    p.add_argument("--skip-mmwave", action="store_true")
    args = p.parse_args()

    list_serial()
    list_video()
    if not args.skip_mmwave:
        detect_mmwave()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

