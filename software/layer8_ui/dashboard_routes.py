"""Thin shim — all routes moved to ``layer8_ui/routes/`` subpackage."""

from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse

from layer8_ui.routes import build_router as _build_router


def build_router(layer8_dir: str | Path) -> APIRouter:
    """Forward to ``layer8_ui.routes.build_router``."""
    return _build_router(layer8_dir)


def index_handler(static_dir: Path) -> FileResponse:
    index_path = Path(static_dir) / "index.html"
    if not index_path.is_file():
        raise HTTPException(404, "static/index.html missing")
    return FileResponse(index_path)
