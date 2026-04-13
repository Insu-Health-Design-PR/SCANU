#!/usr/bin/env python3
"""
Quick device checker for Jetson/Linux.

Lists:
- Serial devices (useful for mmWave radar CLI/DATA and other UART sensors)
- Video devices (useful for thermal camera and other V4L2 cameras)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ``software/`` (contains ``layer1_radar``) — depth from ``examples/test/``.
_software_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_software_root))

from layer1_radar import SerialManager


def list_serial_devices() -> None:
    print("\n" + "=" * 72)
    print("SERIAL DEVICES")
    print("=" * 72)

    ports = SerialManager.list_all_ports()
    if not ports:
        print("No serial ports found.")
        return

    for p in ports:
        dev = p.get("device", "n/a")
        desc = p.get("description", "") or ""
        manufacturer = p.get("manufacturer", "") or ""
        vid = p.get("vid")
        pid = p.get("pid")

        vidpid = "n/a"
        if vid is not None and pid is not None:
            vidpid = f"{int(vid):04X}:{int(pid):04X}"

        print(f"- {dev}")
        print(f"  description : {desc}")
        print(f"  manufacturer: {manufacturer}")
        print(f"  VID:PID     : {vidpid}")


def list_video_devices() -> None:
    print("\n" + "=" * 72)
    print("VIDEO DEVICES")
    print("=" * 72)

    video_nodes = sorted(Path("/dev").glob("video*"))
    if not video_nodes:
        print("No /dev/video* devices found.")
        return

    for node in video_nodes:
        print(f"- {node}")


def try_identify_mmwave() -> None:
    print("\n" + "=" * 72)
    print("MMWAVE AUTODETECT (BEST EFFORT)")
    print("=" * 72)
    mgr = SerialManager()
    try:
        ports = mgr.find_radar_ports(verbose=False)
        print("mmWave radar candidate found:")
        print(f"  config/CLI : {ports.config_port}")
        print(f"  data       : {ports.data_port}")
        if ports.description:
            print(f"  description: {ports.description}")
    except Exception as exc:
        print(f"No mmWave pair auto-identified: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="List connected serial/video devices")
    parser.add_argument(
        "--no-mmwave-detect",
        action="store_true",
        help="Skip mmWave autodetect step",
    )
    args = parser.parse_args()

    print("Device Check")
    print("Host expects mmWave radar on serial and thermal camera on /dev/video*.")

    list_serial_devices()
    list_video_devices()
    if not args.no_mmwave_detect:
        try_identify_mmwave()

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
