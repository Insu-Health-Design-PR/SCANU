from dataclasses import dataclass

from software.layer6_state_machine.models import RadarRuntimeSpec
from software.layer6_state_machine.sensor_control import SensorControlManager


@dataclass
class _Ports:
    config_port: str
    data_port: str


class FakeSerialManager:
    def __init__(self):
        self.connected = False

    def find_radar_ports(self, verbose=False, config_port=None, data_port=None):
        return _Ports(config_port or "/dev/ttyUSB0", data_port or "/dev/ttyUSB1")

    def connect(self, config_port, data_port):
        self.connected = True

    def disconnect(self):
        self.connected = False


class FakeConfigResult:
    def __init__(self, success=True, errors=None):
        self.success = success
        self.commands_sent = 3
        self.errors = errors or []


class FakeConfigurator:
    def __init__(self, mgr):
        self.mgr = mgr

    def configure(self, config=None):
        if config == "bad":
            return FakeConfigResult(success=False, errors=["bad config"])
        return FakeConfigResult(success=True)

    def configure_from_file(self, path):
        return FakeConfigResult(success=True)


class FakeKillSwitch:
    def __init__(self):
        self.killed = []
        self.usb = []
        self.soft = []

    def try_soft_uart_reset(self, cli, data):
        self.soft.append((cli, data))

    def pids_holding_device(self, dev):
        if dev.endswith("0"):
            return [111]
        return [222]

    def terminate_pids(self, pids, force=False):
        self.killed.append((tuple(pids), force))

    def usb_reset_by_port(self, dev):
        self.usb.append(dev)


def _manager() -> SensorControlManager:
    return SensorControlManager(
        radars=[RadarRuntimeSpec("radar_main", "/dev/ttyUSB0", "/dev/ttyUSB1")],
        serial_manager_factory=FakeSerialManager,
        configurator_factory=FakeConfigurator,
        kill_switch_module=FakeKillSwitch(),
    )


def test_get_status_connected():
    mgr = _manager()
    status = mgr.get_status("radar_main")
    assert status.connected is True
    assert status.config_port == "/dev/ttyUSB0"


def test_apply_config_success_and_failure():
    mgr = _manager()

    ok = mgr.apply_config("radar_main", config_text="good")
    assert ok.success is True

    bad = mgr.apply_config("radar_main", config_text="bad")
    assert bad.success is False


def test_reset_soft_and_manual_controls():
    mgr = _manager()

    reset = mgr.reset_soft("radar_main")
    assert reset.success is True

    blocked = mgr.kill_holders("radar_main", manual_confirm=False)
    assert blocked.success is False

    killed = mgr.kill_holders("radar_main", force=True, manual_confirm=True)
    assert killed.success is True

    usb_blocked = mgr.usb_reset("radar_main", manual_confirm=False)
    assert usb_blocked.success is False

    usb_ok = mgr.usb_reset("radar_main", manual_confirm=True)
    assert usb_ok.success is True
