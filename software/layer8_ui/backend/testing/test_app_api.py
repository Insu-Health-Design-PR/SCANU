from fastapi.testclient import TestClient



def test_api_endpoints_exist_and_return_payloads(api_client: TestClient):
    status = api_client.get("/api/status")
    assert status.status_code == 200
    assert "state" in status.json()

    health = api_client.get("/api/health")
    assert health.status_code == 200
    assert "healthy" in health.json()

    alerts = api_client.get("/api/alerts/recent")
    assert alerts.status_code == 200
    assert "alerts" in alerts.json()

    visual = api_client.get("/api/visual/latest")
    assert visual.status_code == 200
    assert "point_cloud" in visual.json()



def test_sensor_status_endpoints_and_control_contracts(api_client: TestClient):
    sensors = api_client.get("/api/sensors/status")
    assert sensors.status_code == 200
    data = sensors.json()
    assert "sensors" in data
    assert isinstance(data["sensors"], list)

    one = api_client.get("/api/sensors/status/radar_main")
    assert one.status_code == 200
    assert one.json().get("radar_id") == "radar_main"

    reset = api_client.post("/api/control/reset-soft", json={"radar_id": "radar_main"})
    assert reset.status_code == 200
    assert reset.json().get("action") == "reset_soft"

    reconfig = api_client.post(
        "/api/control/reconfig",
        json={"radar_id": "radar_main", "config_text": "sensorStop"},
    )
    assert reconfig.status_code == 200
    assert reconfig.json().get("action") == "apply_config"

    kill = api_client.post(
        "/api/control/kill-holders",
        json={"radar_id": "radar_main", "force": True, "manual_confirm": False},
    )
    assert kill.status_code == 200
    assert kill.json().get("action") == "kill_holders"
    assert kill.json().get("success") is False

    usb = api_client.post(
        "/api/control/usb-reset",
        json={"radar_id": "radar_main", "manual_confirm": False},
    )
    assert usb.status_code == 200
    assert usb.json().get("action") == "usb_reset"
    assert usb.json().get("success") is False
