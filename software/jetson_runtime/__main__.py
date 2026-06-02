"""CLI entrypoint: python -m jetson_runtime."""

from __future__ import annotations

import argparse
import json

from .config import load_config
from .runtime import run_forever, run_once


def main() -> None:
    parser = argparse.ArgumentParser(description="SCANU shared Jetson runtime")
    parser.add_argument("--config", required=True, help="Path to Jetson JSON config")
    parser.add_argument("--mode", choices=("serve", "local"), default=None)
    parser.add_argument("--once", action="store_true", help="Run one cycle and print a JSON snapshot")
    parser.add_argument("--no-send", action="store_true", help="Build serve payload without posting to Main")
    args = parser.parse_args()

    config = load_config(args.config, mode_override=args.mode)
    if args.once:
        snapshot = run_once(config, send=not args.no_send)
        print(
            json.dumps(
                {
                    "mode": snapshot.mode,
                    "active_layers": list(snapshot.active_layers),
                    "frame_bundle": snapshot.frame_bundle,
                    "register_result": snapshot.register_result,
                    "heartbeat_result": snapshot.heartbeat_result,
                    "frame_send_result": snapshot.frame_send_result,
                },
                indent=2,
            )
        )
        return
    run_forever(config)


if __name__ == "__main__":
    main()
