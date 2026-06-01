"""mmWave radar data routes: /api/mmwave/*, /api/preview/output/mmwave."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from layer1_sensor_hub.mmwave import (
    normalize_mmwave_frame,
    project_frame_to_camera,
    render_top_down_jpeg,
)
from layer8_ui.artifact_paths import resolved_artifact_path
from layer8_ui.routes._helpers import (
    mmwave_projection_config,
    read_last_mmwave_frame,
    read_mmwave_frames_normalized,
)
from layer8_ui.routes.context import RouterContext
from layer8_ui.settings_store import load


def register_mmwave_routes(
    router: APIRouter, ctx: RouterContext
) -> None:
    @router.get("/api/preview/output/mmwave")
    def preview_mmwave_output() -> FileResponse:
        s = load(ctx.layer8_dir)
        sub = (
            (s.get("mmwave") or {}).get("output") or ""
        )
        path = resolved_artifact_path(
            s,
            relative_to_software=str(sub),
            layer8_dir=ctx.layer8_dir,
        )
        if path is None or not path.is_file():
            raise HTTPException(
                404,
                "Output JSON not found. Run mmWave capture "
                "or set output path in settings.",
            )
        return FileResponse(
            path,
            media_type="application/json",
            filename=path.name,
        )

    @router.get("/api/mmwave/output/stream")
    async def stream_mmwave_output() -> StreamingResponse:
        async def event_generator():
            last_frame_number = 0
            while True:
                frame = read_last_mmwave_frame(ctx)
                if frame is not None:
                    fn = frame.get("frame_id", 0)
                    if fn != last_frame_number:
                        last_frame_number = fn
                        objects = (
                            frame.get("objects", [])
                            if isinstance(frame, dict)
                            else []
                        )
                        yield (
                            f"data: "
                            f"{json.dumps({'frame_id': fn, 'objects': objects, 'ts': time.time(), 'presence': len(objects) > 0, 'num_objects': len(objects)})}"
                            f"\n\n"
                        )
                await asyncio.sleep(0.08)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )

    @router.get("/api/mmwave/camera-overlay/stream")
    async def stream_mmwave_camera_overlay() -> StreamingResponse:
        async def overlay_generator():
            last_frame_id = -1
            while True:
                frame = read_last_mmwave_frame(ctx)
                if frame is not None:
                    fn = frame.get("frame_id", 0)
                    if fn != last_frame_id:
                        last_frame_id = fn
                        norm_frame = (
                            normalize_mmwave_frame(frame)
                        )
                        cfg = mmwave_projection_config(ctx)
                        overlay = project_frame_to_camera(
                            norm_frame, cfg
                        )
                        yield (
                            f"data: "
                            f"{json.dumps(overlay)}\n\n"
                        )
                await asyncio.sleep(0.08)

        return StreamingResponse(
            overlay_generator(),
            media_type="text/event-stream",
        )

    @router.get("/api/mmwave/frames")
    def get_mmwave_frames(
        limit: int = 250,
    ) -> dict[str, Any]:
        frames = read_mmwave_frames_normalized(
            ctx, limit=max(1, min(int(limit), 1000))
        )
        return {
            "available": bool(frames),
            "frames": frames,
            "count": len(frames),
        }

    @router.get("/api/mmwave/latest")
    def get_mmwave_latest() -> dict[str, Any]:
        frames = read_mmwave_frames_normalized(ctx, limit=1)
        if not frames:
            return normalize_mmwave_frame(
                {}, fallback_frame_id=0
            ).to_dict()
        return frames[-1]

    @router.get("/api/mmwave/camera-overlay")
    def get_mmwave_camera_overlay() -> dict[str, Any]:
        frames = read_mmwave_frames_normalized(ctx, limit=1)
        frame = normalize_mmwave_frame(
            frames[-1] if frames else {},
            fallback_frame_id=0,
        )
        return project_frame_to_camera(
            frame, mmwave_projection_config(ctx)
        )

    @router.post("/api/mmwave/preview/regenerate")
    def regenerate_mmwave_preview() -> dict[str, Any]:
        frames = read_mmwave_frames_normalized(ctx, limit=1)
        if not frames:
            return {
                "ok": False,
                "error": "no_mmwave_frames",
            }
        frame = normalize_mmwave_frame(frames[-1])
        s = load(ctx.layer8_dir)
        rel = (
            (s.get("mmwave") or {}).get("live_frame")
            or "layer8_ui/artifacts/live_mmwave.jpg"
        )
        out = resolved_artifact_path(
            s,
            relative_to_software=str(rel),
            layer8_dir=ctx.layer8_dir,
        )
        if out is None:
            return {
                "ok": False,
                "error": "invalid_live_frame_path",
            }
        render_top_down_jpeg(
            frame,
            out,
            max_range_m=mmwave_projection_config(
                ctx
            ).max_range_m,
            trail_tracker=ctx.mmwave_trail_tracker,
        )
        return {
            "ok": True,
            "path": str(out),
            "frame_id": frame.frame_id,
        }
