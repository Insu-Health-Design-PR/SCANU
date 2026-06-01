"""Preview routes: /api/preview/video, /api/preview/live, /api/preview/live_direct."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from layer8_ui import sensor_runner
from layer8_ui.artifact_paths import resolved_artifact_path
from layer8_ui.preview_media import (
    THERMAL_JPEG_WAITING,
    WEBCAM_JPEG_WAITING,
    mjpeg_headers,
    mjpeg_placeholder_jpeg,
)
from layer8_ui.routes.context import RouterContext
from layer8_ui.settings_store import load


def register_preview_routes(
    router: APIRouter, ctx: RouterContext
) -> None:
    @router.get("/api/preview/video/{sensor}")
    def preview_video(
        sensor: str,
    ) -> FileResponse:
        s = load(ctx.layer8_dir)
        key = "video"
        sub = (s.get(sensor) or {}).get(key) or ""
        path = resolved_artifact_path(
            s,
            relative_to_software=str(sub),
            layer8_dir=ctx.layer8_dir,
        )
        if path is None or not path.is_file():
            raise HTTPException(
                404,
                "Video file not found. Run capture first, "
                "or fix the video path in settings "
                "(must be under software/ or layer8_ui/).",
            )
        return FileResponse(
            path,
            media_type="video/mp4",
            filename=path.name,
        )

    @router.get("/api/preview/live/{sensor}")
    async def preview_live(
        sensor: str,
    ) -> StreamingResponse:
        s = load(ctx.layer8_dir)
        rel = (s.get(sensor) or {}).get("live_frame") or ""
        path = resolved_artifact_path(
            s,
            relative_to_software=str(rel),
            layer8_dir=ctx.layer8_dir,
        )
        if path is None:
            raise HTTPException(
                404, "live frame path not configured"
            )

        label = {
            "thermal": "Thermal",
            "webcam": "Webcam",
            "mmwave": "mmWave",
        }.get(sensor, sensor)
        missing = mjpeg_placeholder_jpeg(
            f"{label}: no live JPEG yet",
            f"Expected file: {path.name}",
            "Start the sensor runner or fix live_frame in settings.",
        )

        async def mjpeg_stream():
            boundary = "frame"
            while True:
                jpg: bytes | None = None
                if path.is_file():
                    try:
                        raw = path.read_bytes()
                        if raw:
                            jpg = raw
                    except OSError:
                        jpg = None
                if not jpg:
                    jpg = missing
                chunk = (
                    f"--{boundary}\r\n"
                    "Content-Type: image/jpeg\r\n"
                    f"Content-Length: {len(jpg)}\r\n\r\n"
                ).encode("utf-8") + jpg + b"\r\n"
                yield chunk
                await asyncio.sleep(0.2)

        return StreamingResponse(
            mjpeg_stream(),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers=mjpeg_headers(),
        )

    @router.get("/api/preview/live_direct/thermal")
    async def preview_live_direct_thermal() -> StreamingResponse:
        st = sensor_runner.status("thermal", ctx.layer8_dir)
        s = load(ctx.layer8_dir)

        if bool(st.get("running")):
            rel = (
                (s.get("thermal") or {}).get("live_frame") or ""
            )
            rpath = resolved_artifact_path(
                s,
                relative_to_software=str(rel),
                layer8_dir=ctx.layer8_dir,
            )
            runner_missing = mjpeg_placeholder_jpeg(
                "Thermal runner is ON (subprocess holds the camera).",
                "Showing JPEG from thermal.live_frame "
                "if the runner is writing it.",
                (
                    rpath.name
                    if rpath
                    else "configure thermal.live_frame"
                ),
            )

            async def mjpeg_runner_file():
                boundary = "frame"
                while True:
                    jpg: bytes | None = None
                    if rpath is not None and rpath.is_file():
                        try:
                            raw = rpath.read_bytes()
                            if raw:
                                jpg = raw
                        except OSError:
                            jpg = None
                    if not jpg:
                        jpg = runner_missing
                    chunk = (
                        f"--{boundary}\r\n"
                        "Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(jpg)}\r\n\r\n"
                    ).encode("utf-8") + jpg + b"\r\n"
                    yield chunk
                    await asyncio.sleep(0.2)

            return StreamingResponse(
                mjpeg_runner_file(),
                media_type="multipart/x-mixed-replace; "
                "boundary=frame",
                headers=mjpeg_headers(),
            )

        async def mjpeg_stream():
            boundary = "frame"
            ctx.thermal_stream.add_client(s)
            try:
                while True:
                    payload = (
                        ctx.thermal_stream.latest_jpg()
                        or THERMAL_JPEG_WAITING
                    )
                    chunk = (
                        f"--{boundary}\r\n"
                        "Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(payload)}\r\n\r\n"
                    ).encode("utf-8") + payload + b"\r\n"
                    yield chunk
                    await asyncio.sleep(0.03)
            finally:
                ctx.thermal_stream.remove_client()

        return StreamingResponse(
            mjpeg_stream(),
            media_type="multipart/x-mixed-replace; "
            "boundary=frame",
            headers=mjpeg_headers(),
        )

    @router.get("/api/preview/live_direct/webcam")
    async def preview_live_direct_webcam() -> StreamingResponse:
        st = sensor_runner.status("webcam", ctx.layer8_dir)
        s = load(ctx.layer8_dir)

        if bool(st.get("running")):
            rel = (
                (s.get("webcam") or {}).get("live_frame") or ""
            )
            rpath = resolved_artifact_path(
                s,
                relative_to_software=str(rel),
                layer8_dir=ctx.layer8_dir,
            )
            runner_missing = mjpeg_placeholder_jpeg(
                "Webcam runner is ON (subprocess holds the camera).",
                "Showing JPEG from webcam.live_frame "
                "if the runner is writing it.",
                (
                    rpath.name
                    if rpath
                    else "configure webcam.live_frame"
                ),
            )

            async def mjpeg_runner_file():
                boundary = "frame"
                while True:
                    jpg: bytes | None = None
                    if rpath is not None and rpath.is_file():
                        try:
                            raw = rpath.read_bytes()
                            if raw:
                                jpg = raw
                        except OSError:
                            jpg = None
                    if not jpg:
                        jpg = runner_missing
                    chunk = (
                        f"--{boundary}\r\n"
                        "Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(jpg)}\r\n\r\n"
                    ).encode("utf-8") + jpg + b"\r\n"
                    yield chunk
                    await asyncio.sleep(0.2)

            return StreamingResponse(
                mjpeg_runner_file(),
                media_type="multipart/x-mixed-replace; "
                "boundary=frame",
                headers=mjpeg_headers(),
            )

        async def mjpeg_stream():
            boundary = "frame"
            ctx.webcam_stream.add_client(s)
            try:
                while True:
                    payload = (
                        ctx.webcam_stream.latest_jpg()
                        or WEBCAM_JPEG_WAITING
                    )
                    chunk = (
                        f"--{boundary}\r\n"
                        "Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(payload)}\r\n\r\n"
                    ).encode("utf-8") + payload + b"\r\n"
                    yield chunk
                    await asyncio.sleep(0.03)
            finally:
                ctx.webcam_stream.remove_client()

        return StreamingResponse(
            mjpeg_stream(),
            media_type="multipart/x-mixed-replace; "
            "boundary=frame",
            headers=mjpeg_headers(),
        )
