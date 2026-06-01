"""Control compatibility routes: /api/control/reconfig, /api/control/reset-soft."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from layer8_ui.routes._helpers import normalize_route_result
from layer8_ui.routes.context import RouterContext

from .sensors import _restart_all_sensors, _run_all_sensors, _stop_all_sensors


class CompatReconfigRequest(BaseModel):
    radar_id: str = "radar_main"
    config_path: str | None = None
    config_text: str | None = None


class CompatResetSoftRequest(BaseModel):
    radar_id: str = "radar_main"


def register_control_routes(
    router: APIRouter, ctx: RouterContext
) -> None:
    @router.post("/api/control/reconfig")
    def control_reconfig(
        body: CompatReconfigRequest,
    ) -> dict[str, Any]:
        text = (body.config_text or "").lower()
        if "sensorstop" in text and "sensorstart" in text:
            result = _restart_all_sensors(ctx)
            success, details = normalize_route_result(result)
            return {
                "radar_id": body.radar_id,
                "action": "apply_config",
                "success": success,
                "reason": (
                    None if success else "restart_all_failed"
                ),
                "details": details,
            }
        if "sensorstop" in text:
            result = _stop_all_sensors(ctx)
            success, details = normalize_route_result(result)
            return {
                "radar_id": body.radar_id,
                "action": "apply_config",
                "success": success,
                "reason": (
                    None if success else "stop_all_failed"
                ),
                "details": details,
            }
        result = _run_all_sensors(ctx)
        success, details = normalize_route_result(result)
        return {
            "radar_id": body.radar_id,
            "action": "apply_config",
            "success": success,
            "reason": (
                None if success else "run_all_failed"
            ),
            "details": details,
        }

    @router.post("/api/control/reset-soft")
    def control_reset_soft(
        body: CompatResetSoftRequest,
    ) -> dict[str, Any]:
        result = _restart_all_sensors(ctx)
        success, details = normalize_route_result(result)
        return {
            "radar_id": body.radar_id,
            "action": "reset_soft",
            "success": success,
            "reason": (
                None if success else "restart_all_failed"
            ),
            "details": details,
        }
