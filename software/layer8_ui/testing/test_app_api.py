from fastapi.testclient import TestClient

from software.layer8_ui.app import create_app



def test_api_endpoints_exist_and_return_payloads():
    app = create_app()
    client = TestClient(app)

    status = client.get("/api/status")
    assert status.status_code == 200
    assert "state" in status.json()

    health = client.get("/api/health")
    assert health.status_code == 200
    assert "healthy" in health.json()

    alerts = client.get("/api/alerts/recent")
    assert alerts.status_code == 200
    assert "alerts" in alerts.json()
