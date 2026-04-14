from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient

from software.layer8_ui.backend.publisher import BackendPublisher
from software.layer8_ui.backend.ui_prefs_store import UiPrefsStore


REQUIRED_STATUS_KEYS = {
    "state",
    "fused_score",
    "confidence",
    "health",
}

REQUIRED_HEALTH_KEYS = {
    "healthy",
    "has_fault",
    "sensor_online_count",
}

REQUIRED_VISUAL_KEYS = {
    "timestamp_ms",
    "source_mode",
    "rgb_jpeg_b64",
    "thermal_jpeg_b64",
    "point_cloud",
    "presence",
}


def test_frontend_backend_snapshot_contract_shape(api_client: TestClient) -> None:
    """Validate backend payload shape expected by frontend dashboardApi."""

    status = api_client.get("/api/status")
    assert status.status_code == 200
    status_body = status.json()
    assert REQUIRED_STATUS_KEYS.issubset(status_body.keys())
    assert isinstance(status_body["health"], dict)

    health = api_client.get("/api/health")
    assert health.status_code == 200
    health_body = health.json()
    assert REQUIRED_HEALTH_KEYS.issubset(health_body.keys())

    alerts = api_client.get("/api/alerts/recent?limit=50")
    assert alerts.status_code == 200
    alerts_body = alerts.json()
    assert "alerts" in alerts_body
    assert isinstance(alerts_body["alerts"], list)

    visual = api_client.get("/api/visual/latest")
    assert visual.status_code == 200
    visual_body = visual.json()
    assert REQUIRED_VISUAL_KEYS.issubset(visual_body.keys())
    assert isinstance(visual_body["point_cloud"], list)


def test_frontend_backend_ui_preferences_roundtrip(
    app_factory: Callable[..., FastAPI],
    tmp_path: Path,
) -> None:
    """Validate the same preferences payload frontend stores can be read back."""

    prefs_store = UiPrefsStore(path=tmp_path / "ui_prefs_contract_test.json")
    client = TestClient(app_factory(ui_prefs_store=prefs_store))

    payload = {
        "appliedLayout": "Triple View",
        "previewLayout": "Thermal + Point Cloud",
        "focusView": "thermal",
        "layoutStyle": "focus",
        "customModules": {
            "rgb": False,
            "thermal": True,
            "pointCloud": True,
            "presence": True,
            "systemStatus": True,
            "execution": False,
            "console": False,
        },
    }

    post_response = client.post("/api/ui/preferences", json=payload)
    assert post_response.status_code == 200
    assert post_response.json() == payload

    get_response = client.get("/api/ui/preferences")
    assert get_response.status_code == 200
    assert get_response.json() == payload


def test_frontend_backend_websocket_initial_status_contract(
    app_factory: Callable[..., FastAPI],
) -> None:
    """Validate websocket connect contract used by frontend subscription flow."""

    publisher = BackendPublisher()
    client = TestClient(app_factory(publisher=publisher))

    with client.websocket_connect("/ws/events") as ws:
        initial = ws.receive_json()
        assert initial["event_type"] == "status_update"
        assert isinstance(initial["payload"], dict)
        assert REQUIRED_STATUS_KEYS.issubset(initial["payload"].keys())
