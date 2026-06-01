"""Model profile routes: /api/model/*."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from layer8_ui.artifact_paths import resolved_artifact_path, software_root_from_settings
from layer8_ui.routes.context import RouterContext
from layer8_ui.settings_store import load, save

MODEL_PROFILE_WEBCAM_KEYS: tuple[str, ...] = (
    "webcam_device",
    "webcam_width",
    "webcam_height",
    "metrics_json",
    "person_detection_model",
    "weapon_yolo_model",
    "weapon_conf",
    "weapon_min_box_px",
    "weapon_show_yolo_name",
    "weapon_unsafe_threshold",
    "weapon_gun_threshold",
    "weapon_image_size",
    "weapon_gun_conf",
    "weapon_gun_imgsz",
    "weapon_gun_min_box_px",
    "weapon_gun_thermal",
    "weapon_no_gun_yolo",
    "weapon_gun_yolo_model",
    "weapon_extra_args",
)

_PROFILE_FILE_META_KEYS = frozenset(
    {"version", "schema", "__schema__", "_meta"}
)


class ApplyModelProfileBody(BaseModel):
    id: str


class SnapshotModelProfileBody(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    values: dict[str, Any] | None = None


def _model_profiles_path(layer8_dir: Path) -> Path:
    return layer8_dir / "profiles" / "model_profiles.json"


def _load_model_profiles_raw(layer8_dir: Path) -> dict[str, Any]:
    p = _model_profiles_path(layer8_dir)
    if not p.is_file():
        return {}
    with open(p) as f:
        raw = json.load(f)
    return raw if isinstance(raw, dict) else {}


def _coerce_profile_entry(
    pid: str, v: Any
) -> dict[str, Any] | None:
    if not isinstance(v, dict):
        return None
    pid_s = str(pid).strip()
    if not pid_s or pid_s in _PROFILE_FILE_META_KEYS:
        return None
    if "values" in v and isinstance(v.get("values"), dict):
        return {
            "label": str(v.get("label") or pid_s),
            "description": str(v.get("description") or ""),
            "values": dict(v["values"]),
        }
    return {"label": pid_s, "description": "", "values": dict(v)}


def _normalize_profiles_document(
    raw: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if isinstance(raw.get("profiles"), list):
        out: dict[str, dict[str, Any]] = {}
        for p in raw["profiles"]:
            if not isinstance(p, dict):
                continue
            pid = str(p.get("id") or "").strip()
            if not pid:
                continue
            values = (
                p.get("values")
                if isinstance(p.get("values"), dict)
                else p.get("webcam")
            )
            if not isinstance(values, dict):
                values = {}
            out[pid] = {
                "label": str(
                    p.get("label") or p.get("name") or pid
                ),
                "description": str(
                    p.get("description") or ""
                ),
                "values": dict(values),
            }
        return out
    if isinstance(raw.get("profiles"), dict):
        out = {}
        for pid, v in raw["profiles"].items():
            ent = _coerce_profile_entry(pid, v)
            if ent:
                out[str(pid)] = ent
        return out
    out = {}
    for k, v in raw.items():
        if k in _PROFILE_FILE_META_KEYS:
            continue
        ent = _coerce_profile_entry(k, v)
        if ent:
            out[str(k)] = ent
    return out


def _serialize_profiles_to_disk(
    norm: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    disk: dict[str, Any] = {}
    for pid, entry in norm.items():
        disk[pid] = {
            "label": entry.get("label", pid),
            "description": entry.get("description", ""),
            "values": dict(entry.get("values") or {}),
        }
    return disk


def _extract_profile_values(
    webcam: dict[str, Any]
) -> dict[str, Any]:
    return {
        k: webcam[k]
        for k in MODEL_PROFILE_WEBCAM_KEYS
        if k in webcam
    }


def _apply_values_to_webcam(
    webcam: dict[str, Any], values: dict[str, Any]
) -> dict[str, Any]:
    merged = {**webcam, **values}
    pm = merged.get("person_detection_model")
    if pm is not None and str(pm).strip():
        merged["weapon_yolo_model"] = str(pm).strip()
    return merged


def _get_model_profiles_normalized(
    layer8_dir: Path,
) -> dict[str, dict[str, Any]]:
    return _normalize_profiles_document(
        _load_model_profiles_raw(layer8_dir)
    )


def _save_model_profiles(
    layer8_dir: Path, data: dict[str, Any]
) -> None:
    p = _model_profiles_path(layer8_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_file():
        bak = p.with_suffix(".json.bak")
        try:
            shutil.copy2(p, bak)
        except OSError:
            pass
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(p)


def register_model_routes(
    router: APIRouter, ctx: RouterContext
) -> None:
    @router.get("/api/model/options")
    def model_options() -> dict[str, Any]:
        s = load(ctx.layer8_dir)
        sw = software_root_from_settings(s)
        gun_dir = (
            sw
            / "layer4_inference"
            / "trained_models"
            / "gun_detection"
        )
        checkpoints: list[str] = []
        if gun_dir.is_dir():
            checkpoints = sorted(
                {p.name for p in gun_dir.glob("*.pt")}
            )
        suggestions = [
            "yolov8n.pt",
            "yolov8s.pt",
            "yolov8m.pt",
        ]
        person_yolo_options = sorted(
            set(checkpoints) | set(suggestions)
        )
        return {
            "gun_checkpoints": checkpoints,
            "person_yolo_suggestions": suggestions,
            "person_yolo_options": person_yolo_options,
        }

    @router.get("/api/model/profiles")
    def get_model_profiles() -> dict[str, Any]:
        return {
            "profiles": _get_model_profiles_normalized(
                ctx.layer8_dir
            )
        }

    @router.put("/api/model/profiles")
    def put_model_profiles(
        body: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(body, dict):
            raise HTTPException(400, "body must be an object")
        if "profiles" in body and isinstance(
            body["profiles"], dict
        ):
            norm_in = body["profiles"]
        else:
            norm_in = {
                k: v
                for k, v in body.items()
                if k not in _PROFILE_FILE_META_KEYS
            }
        norm: dict[str, dict[str, Any]] = {}
        for pid, v in norm_in.items():
            ent = _coerce_profile_entry(pid, v)
            if ent:
                norm[str(pid)] = ent
        _save_model_profiles(
            ctx.layer8_dir,
            _serialize_profiles_to_disk(norm),
        )
        return {
            "profiles": _get_model_profiles_normalized(
                ctx.layer8_dir
            )
        }

    @router.post("/api/model/profiles/apply")
    def apply_model_profile(
        body: ApplyModelProfileBody,
    ) -> dict[str, Any]:
        pid = body.id.strip()
        if not pid:
            raise HTTPException(400, "id is required")
        norm = _get_model_profiles_normalized(ctx.layer8_dir)
        prof = norm.get(pid)
        if prof is None:
            raise HTTPException(404, "profile not found")
        values = prof.get("values") or {}
        if not isinstance(values, dict):
            raise HTTPException(
                400, "profile.values must be an object"
            )
        current = load(ctx.layer8_dir)
        w = _apply_values_to_webcam(
            {**(current.get("webcam") or {})}, values
        )
        w["active_model_profile_id"] = pid
        current["webcam"] = w
        save(ctx.layer8_dir, current)
        return load(ctx.layer8_dir)

    @router.post("/api/model/profiles/snapshot")
    def snapshot_model_profile(
        body: SnapshotModelProfileBody,
    ) -> dict[str, Any]:
        pid = body.id.strip()
        if not pid:
            raise HTTPException(400, "id is required")
        s = load(ctx.layer8_dir)
        w_prev = s.get("webcam") or {}
        if body.values is not None and isinstance(
            body.values, dict
        ):
            w_merged = _apply_values_to_webcam(
                dict(w_prev), body.values
            )
            snap = _extract_profile_values(w_merged)
        else:
            snap = _extract_profile_values(w_prev)
        norm = _get_model_profiles_normalized(ctx.layer8_dir)
        name = (body.name or "").strip() or pid
        desc = (body.description or "").strip()
        prev = norm.get(pid)
        entry: dict[str, Any] = {
            "label": name,
            "description": (
                desc
                if desc
                else (
                    prev.get("description", "")
                    if prev
                    else ""
                )
            ),
            "values": snap,
        }
        if prev:
            if not (body.name or "").strip():
                entry["label"] = prev.get("label", pid)
            if not desc:
                entry["description"] = prev.get(
                    "description", ""
                )
        norm[pid] = entry
        _save_model_profiles(
            ctx.layer8_dir,
            _serialize_profiles_to_disk(norm),
        )
        return {"profiles": norm}

    @router.post("/api/model/profiles/sync_from_config")
    def sync_profile_from_config(
        body: ApplyModelProfileBody,
    ) -> dict[str, Any]:
        pid = body.id.strip()
        if not pid:
            raise HTTPException(400, "id is required")
        s = load(ctx.layer8_dir)
        w = s.get("webcam") or {}
        snap = _extract_profile_values(w)
        norm = _get_model_profiles_normalized(ctx.layer8_dir)
        prev = norm.get(pid)
        if prev is None:
            norm[pid] = {
                "label": pid,
                "description": "",
                "values": dict(snap),
            }
        else:
            merged_vals = {
                **(prev.get("values") or {}),
                **snap,
            }
            norm[pid] = {**prev, "values": merged_vals}
        _save_model_profiles(
            ctx.layer8_dir,
            _serialize_profiles_to_disk(norm),
        )
        return {"profiles": norm}
