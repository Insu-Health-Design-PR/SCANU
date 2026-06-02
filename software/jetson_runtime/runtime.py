"""Runtime orchestration for Jetson serve/local modes."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from layer8_ui.settings_store import load as load_layer8_settings
from layer8_ui.settings_store import save as save_layer8_settings

from .bundle import build_frame_bundle
from .config import JetsonRuntimeConfig
from .main_client import MainClient
from .modes import mode_layers


@dataclass(frozen=True)
class RuntimeSnapshot:
    mode: str
    active_layers: tuple[int, ...]
    frame_bundle: dict[str, Any] | None = None
    register_result: dict[str, Any] | None = None
    heartbeat_result: dict[str, Any] | None = None
    frame_send_result: dict[str, Any] | None = None


def apply_layer8_mode(config: JetsonRuntimeConfig) -> None:
    """Persist the Jetson mode into Layer 8 settings for local API visibility."""

    current = load_layer8_settings(config.layer8_dir)
    merged = {
        **current,
        **config.layer8_settings,
    }
    merged["mmwave"] = {
        **(current.get("mmwave") or {}),
        **((config.layer8_settings.get("mmwave") or {}) if isinstance(config.layer8_settings.get("mmwave"), dict) else {}),
        "mode": config.mode,
    }
    save_layer8_settings(config.layer8_dir, merged)


def run_once(config: JetsonRuntimeConfig, *, send: bool = True) -> RuntimeSnapshot:
    """Execute one runtime cycle. Useful for smoke tests and cron-like runs."""

    apply_layer8_mode(config)
    active_layers = mode_layers(config.mode)
    if config.mode == "local":
        return RuntimeSnapshot(mode=config.mode, active_layers=active_layers)

    bundle = build_frame_bundle(config)
    register_result = None
    heartbeat_result = None
    frame_send_result = None
    if send:
        client = MainClient(config)
        register_result = client.register()
        heartbeat_result = client.heartbeat(bundle.get("health", {}))
        frame_send_result = client.send_frame(bundle)
    return RuntimeSnapshot(
        mode=config.mode,
        active_layers=active_layers,
        frame_bundle=bundle,
        register_result=register_result,
        heartbeat_result=heartbeat_result,
        frame_send_result=frame_send_result,
    )


def run_forever(config: JetsonRuntimeConfig) -> None:
    """Run the Jetson runtime loop."""

    apply_layer8_mode(config)
    if config.mode == "local":
        while True:
            time.sleep(5.0)

    client = MainClient(config)
    client.register()
    while True:
        bundle = build_frame_bundle(config)
        client.heartbeat(bundle.get("health", {}))
        client.send_frame(bundle)
        time.sleep(max(0.05, config.send_interval_s))
