from software.layer1_sensor_hub import MultiSensorHub


class _FakeMmwaveSource:
    def read_frame(self, timeout_ms: int = 0):
        return b"raw"


class _FakeMmwaveParser:
    def parse(self, raw: bytes):
        class Parsed:
            frame_number = 123
            points = [1, 2]

        return Parsed()


class _FakePresenceSource:
    def __init__(self):
        class Provider:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        self._provider = Provider()

    def read_frame(self):
        class Presence:
            frame_number = 1
            presence_raw = 0.5
            motion_raw = 0.2
            distance_m = 1.4

        return Presence()


class _FakeThermalSource:
    def __init__(self):
        self.closed = False

    def read_colormap_bgr(self):
        class Frame:
            shape = (480, 640, 3)

        return Frame()

    def close(self):
        self.closed = True


def test_multi_sensor_hub_reads_all_sources():
    hub = MultiSensorHub(
        mmwave_source=_FakeMmwaveSource(),
        mmwave_parser=_FakeMmwaveParser(),
        presence_source=_FakePresenceSource(),
        thermal_source=_FakeThermalSource(),
    )

    frame = hub.read_frame(mmwave_timeout_ms=50)

    assert frame.frame_number == 1
    assert frame.mmwave_frame is not None
    assert len(frame.mmwave_frame.points) == 2
    assert frame.presence_frame is not None
    assert frame.thermal_frame_bgr is not None


def test_multi_sensor_hub_close_calls_sources():
    presence = _FakePresenceSource()
    thermal = _FakeThermalSource()
    hub = MultiSensorHub(
        mmwave_source=None,
        mmwave_parser=None,
        presence_source=presence,
        thermal_source=thermal,
    )

    hub.close()
    assert thermal.closed is True
    assert presence._provider.closed is True

