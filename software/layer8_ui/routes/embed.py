"""Embedded viewer routes: /embed/thermal, /embed/webcam."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from layer8_ui.routes.context import RouterContext


def register_embed_routes(
    router: APIRouter, ctx: RouterContext
) -> None:
    @router.get("/embed/thermal")
    def embed_thermal_page() -> FileResponse:
        p = ctx.layer8_dir / "static" / "embed_thermal.html"
        if not p.is_file():
            raise HTTPException(
                404, "static/embed_thermal.html missing"
            )
        return FileResponse(p, media_type="text/html")

    @router.get("/embed/webcam")
    def embed_webcam_page() -> FileResponse:
        p = ctx.layer8_dir / "static" / "embed_webcam.html"
        if not p.is_file():
            raise HTTPException(
                404, "static/embed_webcam.html missing"
            )
        return FileResponse(p, media_type="text/html")
