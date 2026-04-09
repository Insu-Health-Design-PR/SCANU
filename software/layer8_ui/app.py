"""FastAPI app for Layer 8 status and websocket streaming."""

from __future__ import annotations

import asyncio
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .backend_state_store import BackendStateStore
from .publisher import BackendPublisher
from .status_models import to_utc_iso
from .websocket_stream import WebSocketStream


def create_app(
    *,
    store: BackendStateStore | None = None,
    publisher: BackendPublisher | None = None,
) -> FastAPI:
    state_store = store if store is not None else BackendStateStore()
    stream_publisher = publisher if publisher is not None else BackendPublisher()

    app = FastAPI(title="SCAN-U Layer 8 API", version="0.1.0")
    app.state.layer8_store = state_store
    app.state.layer8_publisher = stream_publisher

    @app.get("/api/status")
    def get_status() -> dict:
        return state_store.status_response()

    @app.get("/api/alerts/recent")
    def get_recent_alerts(limit: int = 50) -> dict:
        return {"alerts": state_store.recent_alerts(limit=limit)}

    @app.get("/api/health")
    def get_health() -> dict:
        return state_store.health_response()

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
