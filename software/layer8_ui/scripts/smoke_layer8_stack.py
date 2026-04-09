#!/usr/bin/env python3
"""Quick smoke test for Layer 8 stack REST + WebSocket endpoints."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from urllib.error import URLError
from urllib.request import urlopen

import websockets


def _http_get_json(url: str) -> dict:
    with urlopen(url, timeout=5) as response:  # nosec B310 - local smoke URL
        payload = response.read().decode("utf-8")
        return json.loads(payload)


async def _read_ws(uri: str, count: int) -> list[dict]:
    events: list[dict] = []
    async with websockets.connect(uri, open_timeout=5, close_timeout=5) as ws:
        for _ in range(count):
            raw = await asyncio.wait_for(ws.recv(), timeout=8)
            events.append(json.loads(raw))
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Layer 8 REST/WS")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--ws-count", type=int, default=8)
    args = parser.parse_args()

    base = f"http://{args.host}:{args.port}"
    ws_uri = f"ws://{args.host}:{args.port}/ws/events"

    try:
        status = _http_get_json(f"{base}/api/status")
        health = _http_get_json(f"{base}/api/health")
        alerts = _http_get_json(f"{base}/api/alerts/recent?limit=5")
    except URLError as exc:
        print(f"[FAIL] HTTP check failed: {exc}")
        return 1

    print("[OK] GET /api/status ->", status.get("state"))
    print("[OK] GET /api/health ->", {"healthy": health.get("healthy"), "state": health.get("state")})
    print("[OK] GET /api/alerts/recent -> count", len(alerts.get("alerts", [])))

    try:
        events = asyncio.run(_read_ws(ws_uri, args.ws_count))
    except Exception as exc:
        print(f"[FAIL] WebSocket check failed: {exc}")
        return 1

    event_types = [evt.get("event_type") for evt in events]
    print("[OK] WS events ->", event_types)

    required = {"status_update", "heartbeat"}
    seen = set(event_types)
    missing = sorted(required - seen)
    if missing:
        print(f"[FAIL] Missing required WS events: {missing}")
        return 1

    print("[PASS] Layer 8 smoke test completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
