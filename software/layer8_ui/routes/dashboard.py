"""Dashboard aggregate routes: /api/dashboard/metrics, /api/status, /api/health, /api/alerts/*, /api/layers/*."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from layer8_ui.artifact_paths import resolved_artifact_path
from layer8_ui.routes._helpers import (
    alerts_payload,
    health_payload,
    layers_summary_payload,
    read_metrics,
    status_payload,
)
from layer8_ui.routes.context import RouterContext
from layer8_ui.settings_store import load


def register_dashboard_routes(
    router: APIRouter, ctx: RouterContext
) -> None:
    @router.get("/api/dashboard/metrics")
    def dashboard_metrics() -> dict[str, Any]:
        return read_metrics(ctx)

    @router.get("/api/status")
    def all_status() -> dict[str, Any]:
        return status_payload(ctx)

    @router.get("/api/health")
    def get_health() -> dict[str, Any]:
        return health_payload(ctx)

    @router.get("/api/alerts/recent")
    def get_recent_alerts(limit: int = 50) -> dict[str, Any]:
        return alerts_payload(ctx, limit=limit)

    @router.get("/api/alerts/history")
    def get_alerts_history(
        from_iso: str = "", to_iso: str = ""
    ) -> dict[str, Any]:
        if ctx.layer7_bridge is None:
            return {"alerts": [], "total": 0}
        all_alerts = ctx.layer7_bridge.logger.recent(
            limit=5000
        )
        filtered = []
        for a in all_alerts:
            ts = a.timestamp_utc
            if from_iso and ts < from_iso:
                continue
            if to_iso and ts > to_iso:
                continue
            filtered.append(
                {
                    "event_id": a.event_id,
                    "level": str(a.level.value),
                    "timestamp_utc": ts,
                    "message": a.message,
                    "state": a.state,
                    "radar_id": a.radar_id,
                    "scores": a.scores,
                    "metadata": a.metadata,
                }
            )
        return {"alerts": filtered, "total": len(filtered)}

    @router.get("/api/layers/summary")
    def get_layers_summary() -> dict[str, Any]:
        return layers_summary_payload(ctx)

    @router.get("/api/layer3/features/latest")
    def get_layer3_features_latest() -> dict[str, Any]:
        s = load(ctx.layer8_dir)
        rel = (
            (s.get("mmwave") or {}).get("layer3_output")
            or "layer8_ui/artifacts/layer3_features.json"
        )
        path = resolved_artifact_path(
            s,
            relative_to_software=str(rel),
            layer8_dir=ctx.layer8_dir,
        )
        if path is None or not path.is_file():
            return {"available": False, "features": None}
        try:
            frames = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return {"available": False, "features": None}
        if not isinstance(frames, list) or not frames:
            return {"available": False, "features": None}
        latest = frames[-1]
        vector = (
            latest.get("vector", [])
            if isinstance(latest, dict)
            else []
        )
        return {
            "available": True,
            "frame_count": len(frames),
            "features": {
                "frame_number": latest.get("frame_number"),
                "timestamp_ms": latest.get("timestamp_ms"),
                "vector": (
                    vector if isinstance(vector, list) else []
                ),
                "details": latest.get("features"),
            },
        }
