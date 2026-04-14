#!/usr/bin/env python3
"""Basic Infineon 60GHz presence detector with event timeline output."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
import sys

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from software.layer1_sensor_hub.infeneon import IfxLtr11PresenceProvider


def _zone_from_presence(presence: float) -> str:
    # LTR11 does not provide direct range in this flow; this is a proxy zone.
    if presence >= 0.70:
        return "near"
    if presence >= 0.45:
        return "mid"
    if presence >= 0.20:
        return "far"
    return "none"


def _direction_label(meta: dict) -> str:
    direction = meta.get("direction")
    if direction is True:
        return "approaching_or_away"
    if direction is False:
        return "steady_or_unknown"
    return "unknown"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Basic IFX 60GHz presence detector")
    p.add_argument("--ifx-uuid", default=None, help="Optional IFX UUID")
    p.add_argument("--duration-s", type=float, default=30.0, help="Capture duration in seconds")
    p.add_argument("--interval-s", type=float, default=0.2, help="Sampling interval in seconds")
    p.add_argument("--presence-th", type=float, default=0.45, help="Presence threshold for detection")
    p.add_argument("--motion-th", type=float, default=0.35, help="Motion threshold for detection")
    p.add_argument("--cooldown-s", type=float, default=1.0, help="Minimum time between events")
    p.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path. Default: software/layer1_sensor_hub/testing/view/ifx_events_<timestamp>.json",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()
    provider = IfxLtr11PresenceProvider(uuid=args.ifx_uuid)

    t0 = time.time()
    end_t = t0 + max(0.5, args.duration_s)
    last_event_end = 0.0
    active_event: dict | None = None
    events: list[dict] = []

    print("Starting IFX basic presence detector...")
    print(f"duration={args.duration_s:.1f}s interval={args.interval_s:.2f}s")
    print(f"thresholds: presence>={args.presence_th:.2f} or motion>={args.motion_th:.2f}")
    print("-" * 96)

    try:
        while time.time() < end_t:
            now = time.time()
            elapsed = now - t0
            presence, motion, _dist = provider.read_sample()
            meta = provider.last_meta or {}

            zone = _zone_from_presence(float(presence))
            direction = _direction_label(meta)
            detected = (presence >= args.presence_th or motion >= args.motion_th) and zone != "none"

            print(
                f"t={elapsed:6.2f}s | presence={presence:0.3f} | motion={motion:0.3f} | "
                f"detected={str(bool(detected)):5s} | zone={zone:4s} | dir={direction}"
            )

            if detected and active_event is None and (now - last_event_end) >= args.cooldown_s:
                active_event = {
                    "start_ts": now,
                    "start_iso": datetime.fromtimestamp(now).isoformat(),
                    "start_elapsed_s": elapsed,
                    "first_presence": float(presence),
                    "max_presence": float(presence),
                    "max_motion": float(motion),
                    "zone_first": zone,
                    "direction_first": direction,
                }
            elif detected and active_event is not None:
                active_event["max_presence"] = max(float(active_event["max_presence"]), float(presence))
                active_event["max_motion"] = max(float(active_event["max_motion"]), float(motion))

            if not detected and active_event is not None:
                active_event["end_ts"] = now
                active_event["end_iso"] = datetime.fromtimestamp(now).isoformat()
                active_event["end_elapsed_s"] = elapsed
                active_event["duration_s"] = float(now - float(active_event["start_ts"]))
                events.append(active_event)
                last_event_end = now
                active_event = None

            if args.interval_s > 0:
                time.sleep(args.interval_s)

        if active_event is not None:
            now = time.time()
            active_event["end_ts"] = now
            active_event["end_iso"] = datetime.fromtimestamp(now).isoformat()
            active_event["end_elapsed_s"] = now - t0
            active_event["duration_s"] = float(now - float(active_event["start_ts"]))
            events.append(active_event)
    finally:
        provider.close()

    print("-" * 96)
    print(f"Detections: {len(events)}")
    for idx, ev in enumerate(events, start=1):
        print(
            f"[{idx}] start={ev['start_elapsed_s']:.2f}s end={ev['end_elapsed_s']:.2f}s "
            f"dur={ev['duration_s']:.2f}s zone={ev['zone_first']} "
            f"p_max={ev['max_presence']:.3f} m_max={ev['max_motion']:.3f}"
        )

    out = args.output
    if not out:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = str(REPO_ROOT / f"software/layer1_sensor_hub/testing/view/ifx_events_{stamp}.json")
    out_path = Path(out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "capture_info": {
            "created_at": datetime.now().isoformat(),
            "duration_s": float(args.duration_s),
            "interval_s": float(args.interval_s),
            "presence_th": float(args.presence_th),
            "motion_th": float(args.motion_th),
        },
        "events": events,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved event list: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

