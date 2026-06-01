"""WebSocket routes: /ws/thermal, /ws/webcam, /ws/events."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from layer8_ui import sensor_runner
from layer8_ui.artifact_paths import resolved_artifact_path
from layer8_ui.preview_media import (
    THERMAL_JPEG_WAITING,
    WEBCAM_JPEG_WAITING,
    mjpeg_placeholder_jpeg,
)
from layer8_ui.routes._helpers import (
    iso_now,
    read_last_mmwave_frame,
    read_metrics,
    status_payload,
    visual_payload,
)
from layer8_ui.routes.context import RouterContext
from layer8_ui.settings_store import load


def register_ws_routes(
    router: APIRouter, ctx: RouterContext
) -> None:
    @router.websocket("/ws/thermal")
    async def websocket_thermal(
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()
        held = False
        last_sent: bytes | None = None
        try:
            while True:
                s = load(ctx.layer8_dir)
                runner_on = bool(
                    sensor_runner.status(
                        "thermal", ctx.layer8_dir
                    ).get("running")
                )
                if runner_on:
                    if held:
                        ctx.thermal_stream.remove_client()
                        held = False
                    rel = (
                        (s.get("thermal") or {}).get(
                            "live_frame"
                        )
                        or ""
                    )
                    rpath = resolved_artifact_path(
                        s,
                        relative_to_software=str(rel),
                        layer8_dir=ctx.layer8_dir,
                    )
                    jpg: bytes | None = None
                    if rpath is not None and rpath.is_file():
                        try:
                            raw = await asyncio.to_thread(
                                rpath.read_bytes
                            )
                            if raw:
                                jpg = raw
                        except OSError:
                            jpg = None
                    if not jpg:
                        jpg = mjpeg_placeholder_jpeg(
                            "Thermal runner is ON "
                            "(subprocess holds the camera).",
                            "Showing JPEG from "
                            "thermal.live_frame "
                            "if the runner is writing it.",
                            (
                                rpath.name
                                if rpath
                                else "configure "
                                "thermal.live_frame"
                            ),
                        )
                    payload = jpg
                else:
                    if not held:
                        ctx.thermal_stream.add_client(s)
                        held = True
                    else:
                        ctx.thermal_stream.sync_settings(s)
                    payload = (
                        ctx.thermal_stream.latest_jpg()
                        or THERMAL_JPEG_WAITING
                    )
                if payload != last_sent:
                    last_sent = payload
                    await websocket.send_bytes(payload)
                await asyncio.sleep(0.04)
        except (
            WebSocketDisconnect,
            ConnectionResetError,
            BrokenPipeError,
        ):
            pass
        finally:
            if held:
                ctx.thermal_stream.remove_client()

    @router.websocket("/ws/webcam")
    async def websocket_webcam(
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()
        held = False
        last_sent: bytes | None = None
        try:
            while True:
                s = load(ctx.layer8_dir)
                runner_on = bool(
                    sensor_runner.status(
                        "webcam", ctx.layer8_dir
                    ).get("running")
                )
                if runner_on:
                    if held:
                        ctx.webcam_stream.remove_client()
                        held = False
                    rel = (
                        (s.get("webcam") or {}).get(
                            "live_frame"
                        )
                        or ""
                    )
                    rpath = resolved_artifact_path(
                        s,
                        relative_to_software=str(rel),
                        layer8_dir=ctx.layer8_dir,
                    )
                    jpg: bytes | None = None
                    if rpath is not None and rpath.is_file():
                        try:
                            raw = await asyncio.to_thread(
                                rpath.read_bytes
                            )
                            if raw:
                                jpg = raw
                        except OSError:
                            jpg = None
                    if not jpg:
                        jpg = mjpeg_placeholder_jpeg(
                            "Webcam runner is ON "
                            "(subprocess holds the camera).",
                            "Showing JPEG from "
                            "webcam.live_frame "
                            "if the runner is writing it.",
                            (
                                rpath.name
                                if rpath
                                else "configure "
                                "webcam.live_frame"
                            ),
                        )
                    payload = jpg
                else:
                    if not held:
                        ctx.webcam_stream.add_client(s)
                        held = True
                    else:
                        ctx.webcam_stream.sync_settings(s)
                    payload = (
                        ctx.webcam_stream.latest_jpg()
                        or WEBCAM_JPEG_WAITING
                    )
                if payload != last_sent:
                    last_sent = payload
                    await websocket.send_bytes(payload)
                await asyncio.sleep(0.04)
        except (
            WebSocketDisconnect,
            ConnectionResetError,
            BrokenPipeError,
        ):
            pass
        finally:
            if held:
                ctx.webcam_stream.remove_client()

    @router.websocket("/ws/events")
    async def websocket_events(
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()
        try:
            await websocket.send_json(
                {
                    "event_type": "status_update",
                    "payload": status_payload(ctx),
                }
            )
            while True:
                sp = status_payload(ctx)
                vp = visual_payload(ctx)
                metrics = read_metrics(ctx)
                mmwave_frame = read_last_mmwave_frame(ctx)
                await websocket.send_json(
                    {
                        "event_type": "status_update",
                        "payload": sp,
                    }
                )
                await websocket.send_json(
                    {
                        "event_type": "visual_update",
                        "payload": vp,
                    }
                )

                weapon_payload: dict[str, Any] = {
                    "state": sp.get("state", "IDLE"),
                    "fused_score": sp.get(
                        "fused_score", 0.0
                    ),
                    "gun_detected": bool(
                        metrics.get("gun_detected")
                    ),
                    "unsafe_score": float(
                        metrics.get("unsafe_score") or 0.0
                    ),
                }
                if mmwave_frame is not None:
                    wt = mmwave_frame.get("weapon_track")
                    weapon_payload["weapon_confidence"] = (
                        wt.get("weapon_confidence", 0.0)
                        if wt
                        else 0.0
                    )
                    weapon_payload["micro_doppler_bw"] = (
                        float(
                            mmwave_frame.get(
                                "micro_doppler_bw", 0.0
                            )
                            or 0.0
                        )
                    )
                    weapon_payload["doppler_centroid"] = (
                        float(
                            mmwave_frame.get(
                                "doppler_centroid", 0.0
                            )
                            or 0.0
                        )
                    )
                    weapon_payload[
                        "azimuth_static_peak"
                    ] = float(
                        mmwave_frame.get(
                            "azimuth_static_peak", 0.0
                        )
                        or 0.0
                    )
                else:
                    weapon_payload["weapon_confidence"] = 0.0
                    weapon_payload["micro_doppler_bw"] = 0.0
                    weapon_payload["doppler_centroid"] = 0.0
                    weapon_payload[
                        "azimuth_static_peak"
                    ] = 0.0

                await websocket.send_json(
                    {
                        "event_type": "weapon_update",
                        "payload": weapon_payload,
                    }
                )

                if bool(
                    sp.get("health", {}).get("has_fault")
                ):
                    await websocket.send_json(
                        {
                            "event_type": "sensor_fault",
                            "payload": {
                                "timestamp_utc": iso_now(),
                                "message": "No sensors "
                                "are currently running.",
                            },
                        }
                    )
                await asyncio.sleep(1.0)
        except (
            WebSocketDisconnect,
            ConnectionResetError,
            BrokenPipeError,
        ):
            pass
