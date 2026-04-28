#!/usr/bin/env python3
"""Stream presence/motion from Infineon BGT60LTR11AIP (LTR11).

Prereq:
- Build/install `ifxradarsdk` for Jetson/aarch64 (we can do this from `radar_sdk.zip`).

Example:
  python3 software/layer1_radar/infineon/examples/ifx_ltr11_stream.py --seconds 10
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uuid", default=None, help="Optional board UUID to open.")
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--out", default=None, help="Optional output JSONL path.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo_root))

    from software.layer1_radar.infineon import IfxLtr11PresenceProvider, PresenceSource

    provider = IfxLtr11PresenceProvider(uuid=args.uuid)
    source = PresenceSource(provider)

    out_f = None
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_f = out_path.open("w", encoding="utf-8")

    t_end = time.time() + float(args.seconds)
    try:
        while time.time() < t_end:
            frame = source.read_frame()
            print(
                f"{frame.frame_number:06d}  "
                f"presence={frame.presence_raw:.6f}  "
                f"motion={frame.motion_raw:.1f}  "
                f"distance_m={frame.distance_m:.2f}"
            )
            if out_f:
                out_f.write(json.dumps(frame.to_dict()) + "\n")
                out_f.flush()
    finally:
        if out_f:
            out_f.close()
        provider.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

