"""Visual data routes: /api/visual/*."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from layer8_ui.routes._helpers import visual_payload
from layer8_ui.routes.context import RouterContext


def register_visual_routes(
    router: APIRouter, ctx: RouterContext
) -> None:
    @router.get("/api/visual/latest")
    def get_visual_latest() -> dict[str, Any]:
        return visual_payload(ctx)

    @router.get("/api/visual/rgb")
    def get_visual_rgb() -> dict[str, Any]:
        visual = visual_payload(ctx)
        return {
            "timestamp_ms": visual.get("timestamp_ms"),
            "source_mode": visual.get("source_mode"),
            "rgb_jpeg_b64": visual.get("rgb_jpeg_b64"),
            "meta": visual.get("meta", {}),
        }

    @router.get("/api/visual/thermal")
    def get_visual_thermal() -> dict[str, Any]:
        visual = visual_payload(ctx)
        return {
            "timestamp_ms": visual.get("timestamp_ms"),
            "source_mode": visual.get("source_mode"),
            "thermal_jpeg_b64": visual.get("thermal_jpeg_b64"),
            "meta": visual.get("meta", {}),
        }

    @router.get("/api/visual/point-cloud")
    def get_visual_point_cloud() -> dict[str, Any]:
        visual = visual_payload(ctx)
        return {
            "timestamp_ms": visual.get("timestamp_ms"),
            "source_mode": visual.get("source_mode"),
            "point_cloud": visual.get("point_cloud", []),
            "meta": visual.get("meta", {}),
        }

    @router.get("/api/visual/presence")
    def get_visual_presence() -> dict[str, Any]:
        visual = visual_payload(ctx)
        return {
            "timestamp_ms": visual.get("timestamp_ms"),
            "source_mode": visual.get("source_mode"),
            "presence": visual.get("presence"),
            "meta": visual.get("meta", {}),
        }
