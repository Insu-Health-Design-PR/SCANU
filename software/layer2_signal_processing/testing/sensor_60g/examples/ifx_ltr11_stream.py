#!/usr/bin/env python3
"""Stream 60 GHz presence with auto provider selection (LTR11 or mock)."""

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
    parser.add_argument("--hz", type=float, default=20.0, help="Sampling rate limit.")
    parser.add_argument("--out", default=None, help="Optional output JSONL path.")
    parser.add_argument("--mock", action="store_true", help="Force mock provider.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[5]
    sys.path.insert(0, str(repo_root))

    from software.layer2_signal_processing.testing.sensor_60g import PresenceProcessor, PresenceSource

    provider_name = "mock"
    if args.mock:
        from software.layer2_signal_processing.testing.sensor_60g import MockPresenceProvider

        provider = MockPresenceProvider()
    else:
        try:
            from software.layer2_signal_processing.testing.sensor_60g import IfxLtr11PresenceProvider

            provider = IfxLtr11PresenceProvider(uuid=args.uuid)
            provider_name = "ltr11"
        except Exception:
            from software.layer2_signal_processing.testing.sensor_60g import MockPresenceProvider

            provider = MockPresenceProvider()

    source = PresenceSource(provider)
    processor = PresenceProcessor()
    print(f"provider={provider_name}")
    dt = 1.0 / max(float(args.hz), 0.1)

    out_f = None
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_f = out_path.open("w", encoding="utf-8")

    t_end = time.time() + float(args.seconds)
    try:
        while time.time() < t_end:
            frame = source.read_frame()
            feat = processor.extract(frame)
            print(
                f"{frame.frame_number:06d}  "
                f"presence={frame.presence_raw:.6f}  "
                f"motion={frame.motion_raw:.1f}  "
                f"score={feat.presence_score:.3f}  "
                f"conf={feat.confidence:.3f}  "
                f"distance_m={frame.distance_m:.2f}"
            )
            if out_f:
                out_f.write(
                    json.dumps(
                        {
                            "frame": frame.to_dict(),
                            "features": feat.to_dict(),
                        }
                    )
                    + "\n"
                )
                out_f.flush()
            time.sleep(dt)
    finally:
        if out_f:
            out_f.close()
        close_fn = getattr(provider, "close", None)
        if callable(close_fn):
            close_fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
