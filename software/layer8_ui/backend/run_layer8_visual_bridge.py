"""Dedicated runner for Layer 8 visual bridge (RGB + thermal + point cloud + presence)."""

from __future__ import annotations

import argparse
import threading

import uvicorn

from software.layer6_state_machine import Layer6Orchestrator

from .app import create_app
from .integration import L6L7ToL8Bridge
from .run_layer8_stack import _producer_loop, build_parser as build_stack_parser
from .visual_state_store import VisualStateStore


def build_parser() -> argparse.ArgumentParser:
    parser = build_stack_parser()
    parser.description = "Run Layer 8 with dedicated visual bridge defaults"
    parser.set_defaults(
        visual="on",
        visual_width=640,
        visual_height=480,
        rgb="on",
        rgb_device=0,
        rgb_width=640,
        rgb_height=480,
        rgb_fps=30,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    orchestrator = Layer6Orchestrator(primary_radar_id=args.radar_id)
    l8_bridge = L6L7ToL8Bridge()
    visual_store = VisualStateStore()

    app = create_app(
        store=l8_bridge.store,
        publisher=l8_bridge.publisher,
        orchestrator=orchestrator,
        visual_store=visual_store,
    )

    stop_event = threading.Event()
    producer = threading.Thread(
        target=_producer_loop,
        kwargs={
            "stop_event": stop_event,
            "l8_bridge": l8_bridge,
            "visual_store": visual_store,
            "args": args,
            "orchestrator": orchestrator,
        },
        daemon=True,
    )
    producer.start()

    try:
        uvicorn.run(app, host=args.host, port=args.port)
    finally:
        stop_event.set()
        producer.join(timeout=2.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

