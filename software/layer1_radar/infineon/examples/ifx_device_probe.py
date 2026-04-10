#!/usr/bin/env python3
"""
Probe Infineon IFX CDC device and dump replies.

This is a low-level tool to confirm link-layer framing and capture responses
without requiring the full Infineon Radar SDK.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from software.layer1_radar.infineon.ifx_cdc_transport import IfxCdcTransport


def main() -> int:
    p = argparse.ArgumentParser(description="Probe Infineon IFX CDC device")
    p.add_argument(
        "--port",
        default="/dev/serial/by-id/usb-Infineon_IFX_CDC-if00",
        help="Device path (default: stable /dev/serial/by-id link)",
    )
    p.add_argument("--baud", type=int, default=115200)
    args = p.parse_args()

    t = IfxCdcTransport(args.port, baudrate=args.baud)
    try:
        print(f"Opened: {args.port} @ {args.baud}")
        for cmd in [0x00, 0x01, 0x02, 0x10, 0x20, 0x30, 0x40, 0x55, 0xAA, 0xFF]:
            rep = t.request_cmd4(cmd)
            print(f"cmd=0x{cmd:02X} reply={rep.payload.hex()} crc_ok={rep.crc_ok}")
        return 0
    finally:
        t.close()


if __name__ == "__main__":
    raise SystemExit(main())

