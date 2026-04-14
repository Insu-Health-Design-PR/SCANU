from __future__ import annotations

import os
from typing import Any, Callable

import pytest
from fastapi import FastAPI

from software.layer6_state_machine.models import ControlResult, SensorStatus


# Prevent import-time global app bootstrap that can pull hardware/runtime side effects.
os.environ.setdefault("LAYER8_APP_SKIP_GLOBAL_BOOT", "1")


class _FakeSensorControl:
    def list_radar_ids(self) -> tuple[str, ...]:
        return ("radar_main",)


class FakeLayer6Orchestrator:
    def __init__(self) -> None:
        self.sensor_control = _FakeSensorControl()

    def get_status(self, radar_id: str) -> SensorStatus:
        return SensorStatus(
            radar_id=radar_id,
            connected=True,
            configured=True,
            streaming=True,
            fault_code=None,
            last_seen_ms=1_700_000_000_000,
            config_port="/dev/tty.usbmodem_cfg",
            data_port="/dev/tty.usbmodem_data",
        )

    def apply_config(self, radar_id: str, *, config_path: str | None = None, config_text: str | None = None) -> ControlResult:
        _ = (config_path, config_text)
        return ControlResult(
            radar_id=radar_id,
            action="apply_config",
            success=True,
            message="Radar configured",
            details={"source": "test"},
        )

    def reset_soft(self, radar_id: str) -> ControlResult:
        return ControlResult(
            radar_id=radar_id,
            action="reset_soft",
            success=True,
            message="Soft reset executed",
            details={},
        )

    def kill_holders(self, radar_id: str, *, force: bool = False, manual_confirm: bool = False) -> ControlResult:
        _ = (force, manual_confirm)
        return ControlResult(
            radar_id=radar_id,
            action="kill_holders",
            success=False,
            message="Manual confirmation required",
            details={},
        )

    def usb_reset(self, radar_id: str, *, manual_confirm: bool = False) -> ControlResult:
        _ = manual_confirm
        return ControlResult(
            radar_id=radar_id,
            action="usb_reset",
            success=False,
            message="Manual confirmation required",
            details={},
        )


@pytest.fixture
def fake_orchestrator() -> FakeLayer6Orchestrator:
    return FakeLayer6Orchestrator()


@pytest.fixture
def app_factory(fake_orchestrator: FakeLayer6Orchestrator) -> Callable[..., FastAPI]:
    from software.layer8_ui.backend.app import create_app

    def _make(**kwargs: Any) -> FastAPI:
        kwargs.setdefault("orchestrator", fake_orchestrator)
        return create_app(**kwargs)

    return _make


@pytest.fixture
def api_client(app_factory: Callable[..., FastAPI]):
    from fastapi.testclient import TestClient

    return TestClient(app_factory())
