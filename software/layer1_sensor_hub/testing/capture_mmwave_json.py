#!/usr/bin/env python3
"""Capture mmWave frames and save parsed output as JSON."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from software.layer1_sensor_hub.mmwave import RadarConfigurator, SerialManager, TLVParser, UARTSource


def main() -> int:
    p = argparse.ArgumentParser(description="Capture mmWave parsed frames into JSON")
    p.add_argument("--frames", "-n", type=int, default=120, help="Number of frames to capture")
    p.add_argument("--output", "-o", default="mmwave_capture.json", help="Output JSON path")
    p.add_argument("--cli-port", default=None, help="Optional explicit CLI port")
    p.add_argument("--data-port", default=None, help="Optional explicit DATA port")
    p.add_argument(
        "--config",
        default="software/layer1_sensor_hub/testing/configs/mmwave_main.cfg",
        help="Path to mmWave .cfg file",
    )
    p.add_argument("--skip-config", action="store_true", help="Skip RadarConfigurator.configure()")
    args = p.parse_args()

    mgr = SerialManager()
    started = time.time()
    captured: list[dict] = []

    try:
        ports = mgr.find_radar_ports(verbose=False, config_port=args.cli_port, data_port=args.data_port)
        mgr.connect(ports.config_port, ports.data_port)

        if not args.skip_config:
            cfg_path = Path(args.config).expanduser().resolve()
            if not cfg_path.exists():
                raise RuntimeError(
                    f"mmWave config file not found: {cfg_path}. "
                    "Add a .cfg under testing/configs or pass --config explicitly."
                )
            cfg = RadarConfigurator(mgr).configure_from_file(cfg_path)
            if not cfg.success:
                raise RuntimeError(f"Configuration failed: {cfg.errors[:5]}")

        src = UARTSource(mgr)
        parser = TLVParser()
        mgr.flush_data_port()
        src.clear_buffer()

        for i, raw in enumerate(src.stream_frames(max_frames=args.frames), start=1):
            parsed = parser.parse(raw)
            captured.append(
                {
                    "frame_number": parsed.frame_number,
                    "timestamp_cycles": parsed.timestamp_cycles,
                    "points": [p.to_dict() for p in parsed.points],
                    "num_points": len(parsed.points),
                    "stats": parsed.stats,
                    "has_range_profile": parsed.range_profile is not None,
                    "has_noise_profile": parsed.noise_profile is not None,
                }
            )
            print(f"\rCaptured {i}/{args.frames}", end="")

        print()
        out_path = Path(args.output).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "capture_info": {
                        "frames": len(captured),
                        "duration_s": time.time() - started,
                    },
                    "frames": captured,
                },
                f,
                indent=2,
            )
        print(f"Saved JSON: {out_path}")
        return 0
    finally:
        try:
            mgr.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
