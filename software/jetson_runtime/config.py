"""Configuration loader for the shared Jetson runtime."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

RuntimeMode = Literal["serve", "local"]


def _repo_software_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _as_path(value: str | Path, *, software_root: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (software_root / path).resolve()


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


@dataclass(frozen=True)
class JetsonRuntimeConfig:
    """Runtime identity and paths for one physical Jetson."""

    jetson_id: str
    mode: RuntimeMode
    main_url: str = ""
    location: str = ""
    software_root: Path = field(default_factory=_repo_software_root)
    layer8_dir: Path = field(default_factory=lambda: _repo_software_root() / "layer8_ui")
    artifacts_dir: Path = field(default_factory=lambda: _repo_software_root() / "layer8_ui" / "artifacts")
    logs_dir: Path = field(default_factory=lambda: _repo_software_root() / "layer8_ui" / "logs")
    sensors: dict[str, Any] = field(default_factory=dict)
    layer8_settings: dict[str, Any] = field(default_factory=dict)
    send_interval_s: float = 0.5

    def with_mode(self, mode: RuntimeMode) -> "JetsonRuntimeConfig":
        return JetsonRuntimeConfig(
            jetson_id=self.jetson_id,
            mode=mode,
            main_url=self.main_url,
            location=self.location,
            software_root=self.software_root,
            layer8_dir=self.layer8_dir,
            artifacts_dir=self.artifacts_dir,
            logs_dir=self.logs_dir,
            sensors=dict(self.sensors),
            layer8_settings=dict(self.layer8_settings),
            send_interval_s=self.send_interval_s,
        )


def load_config(path: str | Path, *, mode_override: str | None = None) -> JetsonRuntimeConfig:
    """Load a Jetson config file with environment overrides."""

    config_path = Path(path).expanduser().resolve()
    with open(config_path) as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("Jetson config must be a JSON object.")

    env_jetson_id = os.environ.get("JETSON_ID", "").strip()
    env_mode = os.environ.get("JETSON_MODE", "").strip()
    env_main_url = os.environ.get("JETSON_MAIN_URL", "").strip()

    jetson_id = env_jetson_id or str(raw.get("jetson_id") or "").strip()
    if not jetson_id:
        raise ValueError("jetson_id is required.")

    mode_value = str(mode_override or env_mode or raw.get("mode") or "serve").strip()
    if mode_value not in {"serve", "local"}:
        raise ValueError("mode must be either 'serve' or 'local'.")
    mode = mode_value  # type: ignore[assignment]

    software_root = _as_path(raw.get("software_root") or _repo_software_root(), software_root=config_path.parent)
    layer8_dir = _as_path(raw.get("layer8_dir") or "layer8_ui", software_root=software_root)
    artifacts_dir = _as_path(raw.get("artifacts_dir") or "layer8_ui/artifacts", software_root=software_root)
    logs_dir = _as_path(raw.get("logs_dir") or "layer8_ui/logs", software_root=software_root)

    sensors = raw.get("sensors") if isinstance(raw.get("sensors"), dict) else {}
    layer8_settings = raw.get("layer8_settings") if isinstance(raw.get("layer8_settings"), dict) else {}
    layer8_settings = _deep_merge(
        {
            "software_root": str(software_root),
            "webcam": {},
            "thermal": {},
            "mmwave": {"mode": mode},
        },
        layer8_settings,
    )
    layer8_settings["mmwave"] = {
        **(layer8_settings.get("mmwave") or {}),
        "mode": mode,
    }

    return JetsonRuntimeConfig(
        jetson_id=jetson_id,
        mode=mode,
        main_url=env_main_url or str(raw.get("main_url") or "").rstrip("/"),
        location=str(raw.get("location") or ""),
        software_root=software_root,
        layer8_dir=layer8_dir,
        artifacts_dir=artifacts_dir,
        logs_dir=logs_dir,
        sensors=dict(sensors),
        layer8_settings=dict(layer8_settings),
        send_interval_s=float(raw.get("send_interval_s", 0.5)),
    )
