"""Module map and command preview routes: /api/layer8/module_map, /api/command/{sensor}."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from layer8_ui import sensor_runner
from layer8_ui.routes.context import RouterContext
from layer8_ui.settings_store import load


def register_layer8_routes(
    router: APIRouter, ctx: RouterContext
) -> None:
    @router.get("/api/layer8/module_map")
    def layer8_module_map() -> dict[str, str]:
        return {
            "thermal_tab": "layer8_ui.thermal_runner",
            "webcam_tab": "layer8_ui.webcam_runner",
            "model_tab": (
                "Live webcam infer: layer8_ui.webcam_runner -> "
                "weapon_ai.webcam_layer8_runner "
                "-> weapon_ai.infer_thermal_objects "
                "(layer4_inference/weapon_ai/infer_thermal_objects.py). "
                "layer8_ui.inference_overlay is a stub "
                "for optional server-side overlays."
            ),
            "mmwave_tab": "layer8_ui.sensor_runner (mmWave CLI)",
        }

    @router.get("/api/command/{sensor}")
    def preview_command(sensor: str) -> dict[str, Any]:
        if sensor not in ("thermal", "webcam", "mmwave"):
            raise HTTPException(400, "invalid sensor")
        s = load(ctx.layer8_dir)
        cmd = sensor_runner.build_command(
            sensor, s, ctx.layer8_dir
        )
        run_cwd = str(
            sensor_runner.command_cwd(
                sensor, s, ctx.layer8_dir
            )
        )
        return {
            "command": cmd,
            "cwd": run_cwd,
            "software_root": str(
                sensor_runner.resolved_software_root(s)
            ),
        }
