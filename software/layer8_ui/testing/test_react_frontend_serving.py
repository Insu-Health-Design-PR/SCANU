from pathlib import Path

from fastapi.testclient import TestClient

from layer8_ui.app import FRONTEND_DIST, LAYER8_DIR, app
from layer8_ui.settings_store import settings_path


def test_root_serves_react_build_when_available():
    assert Path(FRONTEND_DIST / "index.html").is_file()

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "/assets/" in response.text
    assert '<div id="root">' in response.text


def test_operator_state_and_mode_endpoints():
    client = TestClient(app)
    settings_file = settings_path(LAYER8_DIR)
    original = settings_file.read_text() if settings_file.is_file() else None

    try:
        state = client.get("/api/operator/state")
        assert state.status_code == 200
        assert "mode" in state.json()
        assert "recovery_state" in state.json()

        changed = client.post("/api/operator/mode/local")
        assert changed.status_code == 200
        assert changed.json()["mode"] == "local"

        restored = client.post("/api/operator/mode/central")
        assert restored.status_code == 200
        assert restored.json()["mode"] == "central"
    finally:
        if original is None:
            settings_file.unlink(missing_ok=True)
        else:
            settings_file.write_text(original)
