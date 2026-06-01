"""Sensor start/stop/restart routes: /api/status/*, /api/run/*, /api/stop/*, /api/restart/*."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from layer8_ui import sensor_runner
from layer8_ui.routes.context import RouterContext
from layer8_ui.settings_store import load

SensorName = str  # "thermal" | "webcam" | "mmwave"


def _run_all_sensors(ctx: RouterContext) -> Any:
    s = load(ctx.layer8_dir)
    results: dict[str, Any] = {}
    started: list[str] = []
    ctx.thermal_stream.pause_for_thermal_subprocess()
    try:
        for sensor in ("thermal", "webcam", "mmwave"):
            if sensor == "webcam":
                ctx.webcam_stream.pause_for_webcam_subprocess()
            try:
                res = sensor_runner.start(sensor, s, ctx.layer8_dir)
            finally:
                if sensor == "webcam":
                    ctx.webcam_stream.resume_after_webcam_subprocess_attempt()
            results[sensor] = res
            if res.get("ok"):
                started.append(sensor)
                continue
            for started_sensor in started:
                sensor_runner.stop(started_sensor, ctx.layer8_dir)
            return JSONResponse(
                {
                    "ok": False,
                    "error": f"Failed to start {sensor}",
                    "results": results,
                },
                status_code=409,
            )
        return {"ok": True, "results": results}
    finally:
        ctx.thermal_stream.resume_after_thermal_subprocess_attempt()


def _stop_all_sensors(ctx: RouterContext) -> dict[str, Any]:
    return {
        "ok": True,
        "results": {
            sensor: sensor_runner.stop(sensor, ctx.layer8_dir)
            for sensor in ("thermal", "webcam", "mmwave")
        },
    }


def _restart_all_sensors(ctx: RouterContext) -> Any:
    sensor_runner.stop("thermal", ctx.layer8_dir)
    sensor_runner.stop("webcam", ctx.layer8_dir)
    sensor_runner.stop("mmwave", ctx.layer8_dir)
    return _run_all_sensors(ctx)


def register_sensor_routes(router: APIRouter, ctx: RouterContext) -> None:
    @router.get("/api/status/stream")
    async def stream_status() -> StreamingResponse:
        async def event_stream():
            while True:
                payload = {
                    name: sensor_runner.status(name, ctx.layer8_dir)
                    for name in ("thermal", "webcam", "mmwave")
                }
                yield f"event: status\ndata: {json.dumps(payload)}\n\n"
                await asyncio.sleep(1.0)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @router.get("/api/status/{sensor}")
    def one_status(sensor: str) -> dict[str, Any]:
        if sensor not in ("thermal", "webcam", "mmwave"):
            return {"ok": False, "error": "invalid sensor"}
        return sensor_runner.status(sensor, ctx.layer8_dir)

    @router.post("/api/run/{sensor}")
    def run_sensor(sensor: str) -> Any:
        if sensor not in ("thermal", "webcam", "mmwave"):
            return JSONResponse({"ok": False, "error": "invalid sensor"}, status_code=400)
        s = load(ctx.layer8_dir)
        if sensor == "thermal":
            ctx.thermal_stream.pause_for_thermal_subprocess()
        if sensor == "webcam":
            ctx.webcam_stream.pause_for_webcam_subprocess()
        try:
            result = sensor_runner.start(sensor, s, ctx.layer8_dir)
        finally:
            if sensor == "thermal":
                ctx.thermal_stream.resume_after_thermal_subprocess_attempt()
            if sensor == "webcam":
                ctx.webcam_stream.resume_after_webcam_subprocess_attempt()
        if not result.get("ok"):
            return JSONResponse(result, status_code=409)
        return result

    @router.post("/api/stop/{sensor}")
    def stop_sensor(sensor: str) -> dict[str, Any]:
        if sensor not in ("thermal", "webcam", "mmwave"):
            return {"ok": False, "error": "invalid sensor"}
        return sensor_runner.stop(sensor, ctx.layer8_dir)

    @router.post("/api/restart/{sensor}")
    def restart_sensor(sensor: str) -> Any:
        if sensor not in ("thermal", "webcam", "mmwave"):
            return JSONResponse({"ok": False, "error": "invalid sensor"}, status_code=400)
        s = load(ctx.layer8_dir)
        if sensor == "thermal":
            ctx.thermal_stream.pause_for_thermal_subprocess()
        if sensor == "webcam":
            ctx.webcam_stream.pause_for_webcam_subprocess()
        try:
            result = sensor_runner.restart(sensor, s, ctx.layer8_dir)
        finally:
            if sensor == "thermal":
                ctx.thermal_stream.resume_after_thermal_subprocess_attempt()
            if sensor == "webcam":
                ctx.webcam_stream.resume_after_webcam_subprocess_attempt()
        if not result.get("ok"):
            return JSONResponse(result, status_code=409)
        return result

    @router.post("/api/run_all")
    def run_all_sensors() -> Any:
        return _run_all_sensors(ctx)

    @router.post("/api/stop_all")
    def stop_all_sensors() -> dict[str, Any]:
        return _stop_all_sensors(ctx)

    @router.post("/api/restart_all")
    def restart_all_sensors() -> Any:
        return _restart_all_sensors(ctx)
