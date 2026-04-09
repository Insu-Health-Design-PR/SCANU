"""FastAPI app for Layer 8 status and websocket streaming."""

from __future__ import annotations

import asyncio
import time
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from software.layer6_state_machine import Layer6Orchestrator
from software.layer6_state_machine.models import ControlResult, SensorStatus

from .backend_state_store import BackendStateStore
from .publisher import BackendPublisher
from .status_models import to_utc_iso
from .visual_state_store import VisualStateStore
from .websocket_stream import WebSocketStream


class ReconfigRequest(BaseModel):
    radar_id: str = Field(default="radar_main")
    config_path: str | None = None
    config_text: str | None = None


class ResetSoftRequest(BaseModel):
    radar_id: str = Field(default="radar_main")


class KillHoldersRequest(BaseModel):
    radar_id: str = Field(default="radar_main")
    force: bool = False
    manual_confirm: bool = False


class UsbResetRequest(BaseModel):
    radar_id: str = Field(default="radar_main")
    manual_confirm: bool = False


def create_app(
    *,
    store: BackendStateStore | None = None,
    publisher: BackendPublisher | None = None,
    orchestrator: Layer6Orchestrator | None = None,
    visual_store: VisualStateStore | None = None,
) -> FastAPI:
    state_store = store if store is not None else BackendStateStore()
    stream_publisher = publisher if publisher is not None else BackendPublisher()
    layer6 = orchestrator if orchestrator is not None else Layer6Orchestrator()
    visual = visual_store if visual_store is not None else VisualStateStore()

    app = FastAPI(title="SCAN-U Layer 8 API", version="0.2.0")
    app.state.layer8_store = state_store
    app.state.layer8_publisher = stream_publisher
    app.state.layer6_orchestrator = layer6
    app.state.layer8_visual_store = visual

    def _publish_control_result(result: ControlResult) -> None:
        stream_publisher.publish(WebSocketStream.encode_control_result(result))

    def _sensor_status_or_404(radar_id: str) -> SensorStatus:
        try:
            return layer6.get_status(radar_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/status")
    def get_status() -> dict:
        return state_store.status_response()

    @app.get("/api/alerts/recent")
    def get_recent_alerts(limit: int = 50) -> dict:
        return {"alerts": state_store.recent_alerts(limit=limit)}

    @app.get("/api/health")
    def get_health() -> dict:
        return state_store.health_response()

    @app.get("/api/visual/latest")
    def get_visual_latest() -> dict:
        return visual.latest()

    @app.get("/api/visual/rgb")
    def get_visual_rgb() -> dict:
        latest = visual.latest()
        return {
            "timestamp_ms": latest.get("timestamp_ms"),
            "source_mode": latest.get("source_mode"),
            "rgb_jpeg_b64": latest.get("rgb_jpeg_b64"),
            "meta": latest.get("meta", {}),
        }

    @app.get("/api/visual/thermal")
    def get_visual_thermal() -> dict:
        latest = visual.latest()
        return {
            "timestamp_ms": latest.get("timestamp_ms"),
            "source_mode": latest.get("source_mode"),
            "thermal_jpeg_b64": latest.get("thermal_jpeg_b64"),
            "meta": latest.get("meta", {}),
        }

    @app.get("/api/visual/point-cloud")
    def get_visual_point_cloud() -> dict:
        latest = visual.latest()
        return {
            "timestamp_ms": latest.get("timestamp_ms"),
            "source_mode": latest.get("source_mode"),
            "point_cloud": latest.get("point_cloud", []),
            "meta": latest.get("meta", {}),
        }

    @app.get("/api/visual/presence")
    def get_visual_presence() -> dict:
        latest = visual.latest()
        return {
            "timestamp_ms": latest.get("timestamp_ms"),
            "source_mode": latest.get("source_mode"),
            "presence": latest.get("presence"),
            "meta": latest.get("meta", {}),
        }

    @app.get("/api/sensors/status")
    def get_sensors_status() -> dict:
        statuses = [
            asdict(_sensor_status_or_404(radar_id))
            for radar_id in layer6.sensor_control.list_radar_ids()
        ]
        return {"sensors": statuses}

    @app.get("/api/sensors/status/{radar_id}")
    def get_sensor_status(radar_id: str) -> dict:
        return asdict(_sensor_status_or_404(radar_id))

    @app.post("/api/control/reconfig")
    def control_reconfig(body: ReconfigRequest) -> dict:
        result = layer6.apply_config(
            body.radar_id,
            config_path=body.config_path,
            config_text=body.config_text,
        )
        _publish_control_result(result)
        return asdict(result)

    @app.post("/api/control/reset-soft")
    def control_reset_soft(body: ResetSoftRequest) -> dict:
        result = layer6.reset_soft(body.radar_id)
        _publish_control_result(result)
        return asdict(result)

    @app.post("/api/control/kill-holders")
    def control_kill_holders(body: KillHoldersRequest) -> dict:
        result = layer6.kill_holders(
            body.radar_id,
            force=bool(body.force),
            manual_confirm=bool(body.manual_confirm),
        )
        _publish_control_result(result)
        return asdict(result)

    @app.post("/api/control/usb-reset")
    def control_usb_reset(body: UsbResetRequest) -> dict:
        result = layer6.usb_reset(
            body.radar_id,
            manual_confirm=bool(body.manual_confirm),
        )
        _publish_control_result(result)
        return asdict(result)

    @app.websocket("/ws/events")
    async def websocket_events(ws: WebSocket) -> None:
        await ws.accept()
        queue = stream_publisher.subscribe()
        try:
            # Push current status immediately on connect.
            status_payload = state_store.status_response()
            await ws.send_json({"event_type": "status_update", "payload": status_payload})

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    await ws.send_json(event)
                except asyncio.TimeoutError:
                    hb = WebSocketStream.encode_heartbeat(to_utc_iso(time.time() * 1000.0) or "")
                    await ws.send_json(hb)
        except WebSocketDisconnect:
            pass
        finally:
            stream_publisher.unsubscribe(queue)

    return app


app = create_app()
