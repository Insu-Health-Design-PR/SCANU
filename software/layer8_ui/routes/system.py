"""System configuration routes: /api/system/metrics, /api/config."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from layer8_ui import system_metrics
from layer8_ui.routes.context import RouterContext
from layer8_ui.settings_store import DEFAULT_SETTINGS, load, reset_webcam_weapon_defaults, save


class SettingsBody(BaseModel):
    settings: dict[str, Any]


SensorName = str  # "thermal" | "webcam" | "mmwave"


def register_system_routes(router: APIRouter, ctx: RouterContext) -> None:
    @router.get("/api/system/metrics")
    def get_system_metrics() -> dict[str, Any]:
        return system_metrics.snapshot()

    @router.get("/api/config")
    def get_config() -> dict[str, Any]:
        return load(ctx.layer8_dir)

    @router.put("/api/config")
    def put_config(body: SettingsBody) -> dict[str, Any]:
        if not isinstance(body.settings, dict):
            raise HTTPException(400, "settings must be an object")
        save(ctx.layer8_dir, body.settings)
        return load(ctx.layer8_dir)

    @router.post("/api/config/reset")
    def reset_config() -> dict[str, Any]:
        save(ctx.layer8_dir, deepcopy(DEFAULT_SETTINGS))
        return load(ctx.layer8_dir)

    @router.post("/api/config/reset/{sensor}")
    def reset_sensor_config(sensor: str) -> dict[str, Any]:
        if sensor not in ("thermal", "webcam", "mmwave"):
            raise HTTPException(400, "invalid sensor")
        current = load(ctx.layer8_dir)
        current[sensor] = deepcopy(DEFAULT_SETTINGS[sensor])
        save(ctx.layer8_dir, current)
        return load(ctx.layer8_dir)

    @router.post("/api/config/reset/model")
    def reset_model_weapon_defaults() -> dict[str, Any]:
        return reset_webcam_weapon_defaults(ctx.layer8_dir)
