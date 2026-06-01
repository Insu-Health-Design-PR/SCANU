"""UI preferences routes: /api/ui/preferences."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from layer8_ui.routes.context import RouterContext


class UiPreferencesPayload(BaseModel):
    appliedLayout: str = "Triple View"
    previewLayout: str = "Triple View"
    focusView: str = "rgb"
    layoutStyle: str = "grid"
    customModules: dict[str, bool] = {}


def _ui_prefs_path(layer8_dir: Path) -> Path:
    return layer8_dir / "ui_prefs.json"


def _default_ui_prefs() -> dict[str, Any]:
    return {
        "appliedLayout": "Triple View",
        "previewLayout": "Triple View",
        "focusView": "rgb",
        "layoutStyle": "grid",
        "customModules": {
            "rgb": True,
            "thermal": True,
            "pointCloud": True,
            "presence": True,
            "systemStatus": True,
            "execution": True,
            "consoleLog": True,
        },
    }


def _load_ui_prefs(layer8_dir: Path) -> dict[str, Any]:
    p = _ui_prefs_path(layer8_dir)
    base = _default_ui_prefs()
    if not p.is_file():
        return base
    try:
        raw = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return base
    if not isinstance(raw, dict):
        return base
    merged = {**base, **raw}
    custom = raw.get("customModules")
    if isinstance(custom, dict):
        merged["customModules"] = {
            **base["customModules"],
            **custom,
        }
    return merged


def _save_ui_prefs(
    layer8_dir: Path, payload: dict[str, Any]
) -> dict[str, Any]:
    p = _ui_prefs_path(layer8_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    normalized = _default_ui_prefs()
    for k in (
        "appliedLayout",
        "previewLayout",
        "focusView",
        "layoutStyle",
    ):
        if k in payload:
            normalized[k] = payload[k]
    custom = payload.get("customModules")
    if isinstance(custom, dict):
        normalized["customModules"] = {
            **normalized["customModules"],
            **custom,
        }
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(normalized, indent=2))
    tmp.replace(p)
    return normalized


def register_ui_routes(
    router: APIRouter, ctx: RouterContext
) -> None:
    @router.get("/api/ui/preferences")
    def get_ui_preferences() -> dict[str, Any]:
        return _load_ui_prefs(ctx.layer8_dir)

    @router.post("/api/ui/preferences")
    def set_ui_preferences(
        payload: UiPreferencesPayload,
    ) -> dict[str, Any]:
        return _save_ui_prefs(
            ctx.layer8_dir, payload.model_dump()
        )
