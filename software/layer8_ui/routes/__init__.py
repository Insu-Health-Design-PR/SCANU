"""Route subpackage — each module registers routes on the shared ``APIRouter``."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from layer8_ui import thermal_runner, webcam_runner
from layer8_ui.routes.context import RouterContext

from . import (
    control,
    dashboard,
    devices,
    embed,
    layer8 as layer8_module,
    mmwave,
    model,
    preview,
    sensors,
    system,
    ui,
    visual,
    ws,
)

try:
    from layer6_state_machine.models import (
        WeaponStateMachineConfig,
    )
    from layer6_state_machine.orchestrator import Layer6Orchestrator
    from layer6_state_machine.state_machine import StateMachine
except Exception:
    Layer6Orchestrator = None
    WeaponStateMachineConfig = None
    StateMachine = None

try:
    from layer7_alerts.event_logger import EventLogger
    from layer7_alerts.integration import L6ToL7Bridge
except Exception:
    L6ToL7Bridge = None
    EventLogger = None


def build_router(layer8_dir: str | Path) -> APIRouter:
    layer8_dir = Path(layer8_dir).resolve()
    thermal_stream = thermal_runner.get_thermal_shared_stream(layer8_dir)
    webcam_stream = webcam_runner.get_webcam_shared_stream(layer8_dir)

    layer6_orchestrator = (
        Layer6Orchestrator(
            state_machine=StateMachine(
                config=WeaponStateMachineConfig()
            )
        )
        if Layer6Orchestrator is not None
        else None
    )
    layer7_bridge = (
        L6ToL7Bridge(
            logger=EventLogger(
                file_path=layer8_dir / "artifacts" / "alerts.jsonl"
            )
        )
        if L6ToL7Bridge is not None
        else None
    )

    ctx = RouterContext(
        layer8_dir=layer8_dir,
        thermal_stream=thermal_stream,
        webcam_stream=webcam_stream,
        layer6_orchestrator=layer6_orchestrator,
        layer7_bridge=layer7_bridge,
    )

    router = APIRouter()

    system.register_system_routes(router, ctx)
    model.register_model_routes(router, ctx)
    layer8_module.register_layer8_routes(router, ctx)
    preview.register_preview_routes(router, ctx)
    embed.register_embed_routes(router, ctx)
    mmwave.register_mmwave_routes(router, ctx)
    devices.register_device_routes(router, ctx)
    dashboard.register_dashboard_routes(router, ctx)
    visual.register_visual_routes(router, ctx)
    ui.register_ui_routes(router, ctx)
    sensors.register_sensor_routes(router, ctx)
    control.register_control_routes(router, ctx)
    ws.register_ws_routes(router, ctx)

    return router
