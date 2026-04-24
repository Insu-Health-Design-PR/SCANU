"""
Layer 8 sensor dashboard — application entrypoint only.

Run from ``software/``:

  python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088

Routes live in ``dashboard_routes``; runners in ``thermal_runner``, ``webcam_runner``,
``sensor_runner``; media helpers in ``preview_media``; paths in ``artifact_paths``.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from layer8_ui.dashboard_routes import build_router, index_handler

LAYER8_DIR = Path(__file__).resolve().parent
STATIC = LAYER8_DIR / "static"
ARTIFACTS = LAYER8_DIR / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)
API_KEY = os.environ.get("LAYER8_API_KEY", "").strip()
RAW_CORS_ORIGINS = os.environ.get("LAYER8_CORS_ORIGINS", "*").strip()
CORS_ORIGINS = (
    ["*"]
    if RAW_CORS_ORIGINS in {"", "*"}
    else [origin.strip() for origin in RAW_CORS_ORIGINS.split(",") if origin.strip()]
)

app = FastAPI(title="SCANU Layer 8 — sensor runners", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _token_is_valid(token: str | None) -> bool:
    return not API_KEY or token == API_KEY


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path == "/api/health":
        return await call_next(request)
    if request.url.path.startswith("/api/") and not _token_is_valid(request.headers.get("X-Layer8-Api-Key")):
        return JSONResponse({"detail": "Invalid or missing Layer 8 API key."}, status_code=401)
    return await call_next(request)

if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

layer8_router = build_router(LAYER8_DIR)
public_router = APIRouter()
protected_ws_endpoints = {}
for route in layer8_router.routes:
    path = getattr(route, "path", "")
    if path.startswith("/ws/"):
        protected_ws_endpoints[path] = route.endpoint
    else:
        public_router.routes.append(route)


async def _dispatch_protected_websocket(websocket: WebSocket, path: str) -> None:
    if not _token_is_valid(websocket.query_params.get("token")):
        await websocket.close(code=1008)
        return
    endpoint = protected_ws_endpoints.get(path)
    if endpoint is not None:
        await endpoint(websocket)
        return
    await websocket.close(code=1011)


@app.websocket("/ws/events")
async def protected_websocket_events(websocket: WebSocket) -> None:
    await _dispatch_protected_websocket(websocket, "/ws/events")


@app.websocket("/ws/webcam")
async def protected_websocket_webcam(websocket: WebSocket) -> None:
    await _dispatch_protected_websocket(websocket, "/ws/webcam")


@app.websocket("/ws/thermal")
async def protected_websocket_thermal(websocket: WebSocket) -> None:
    await _dispatch_protected_websocket(websocket, "/ws/thermal")


app.include_router(public_router)


@app.get("/")
def index():
    return index_handler(STATIC)
