"""
Layer 8 sensor dashboard — application entrypoint only.

Run from ``software/``:

  python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088

Routes live in ``dashboard_routes``; runners in ``thermal_runner``, ``webcam_runner``,
``sensor_runner``; media helpers in ``preview_media``; paths in ``artifact_paths``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from layer8_ui.dashboard_routes import build_router, index_handler

LAYER8_DIR = Path(__file__).resolve().parent
STATIC = LAYER8_DIR / "static"
ARTIFACTS = LAYER8_DIR / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="SCANU Layer 8 — sensor runners", version="0.1.0")

if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

app.include_router(build_router(LAYER8_DIR))


@app.get("/")
def index():
    return index_handler(STATIC)
