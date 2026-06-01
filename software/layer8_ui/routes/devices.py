"""Device grid and operator routes: /api/devices, /api/operator/*."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter

from layer8_ui.routes._helpers import device_grid_payload, status_payload
from layer8_ui.routes.context import RouterContext
from layer8_ui.settings_store import load, save


def register_device_routes(
    router: APIRouter, ctx: RouterContext
) -> None:
    @router.get("/api/devices")
    def get_devices() -> dict[str, Any]:
        return device_grid_payload(ctx)

    @router.get("/api/operator/state")
    def get_operator_state() -> dict[str, Any]:
        devices = device_grid_payload(ctx)
        status = status_payload(ctx)
        return {
            "timestamp_ms": devices["timestamp_ms"],
            "mode": devices["mode"],
            "recovery_state": devices["recovery_state"],
            "has_fault": bool(
                status.get("health", {}).get("has_fault")
            ),
            "sensor_online_count": int(
                status.get("health", {}).get(
                    "sensor_online_count"
                )
                or 0
            ),
            "reconnect_hint": "auto-refresh active",
        }

    @router.post("/api/operator/mode/{mode}")
    def set_operator_mode(
        mode: Literal["central", "fallback", "local"],
    ) -> dict[str, Any]:
        s = load(ctx.layer8_dir)
        mmwave = dict(s.get("mmwave") or {})
        mmwave["mode"] = mode
        s["mmwave"] = mmwave
        save(ctx.layer8_dir, s)
        return get_operator_state()
