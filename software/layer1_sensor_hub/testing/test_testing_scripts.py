from software.layer1_sensor_hub.testing import (
    capture_mmwave_json,
    capture_thermal_video,
    device_check_hub,
    sensor_approval_hub,
)


def test_import_new_testing_scripts():
    assert capture_mmwave_json is not None
    assert capture_thermal_video is not None
    assert device_check_hub is not None
    assert sensor_approval_hub is not None


def test_argparse_builds_for_new_scripts(monkeypatch):
    monkeypatch.setattr("sys.argv", ["device_check_hub.py", "--skip-mmwave"])
    assert device_check_hub.main() == 0

