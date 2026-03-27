from software.layer1_sensor_hub.testing.run_live_hub import build_parser, run_loop, summarize_frame


class _FakeHub:
    def __init__(self):
        self.calls = 0

    def read_frame(self, mmwave_timeout_ms: int = 0):
        self.calls += 1

        class MMW:
            points = [1, 2, 3]

        class PRS:
            presence_raw = 0.6
            motion_raw = 0.2
            distance_m = 2.0

        class THM:
            shape = (480, 640, 3)

        class Frame:
            frame_number = self.calls
            mmwave_frame = MMW()
            presence_frame = PRS()
            thermal_frame_bgr = THM()

        return Frame()


def test_build_parser_defaults():
    args = build_parser().parse_args(["--config", "software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg"])
    assert args.mmwave == "on"
    assert args.presence == "mock"
    assert args.thermal == "on"
    assert args.max_frames == 0
    assert args.config.endswith("software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg")


def test_summarize_frame_contains_sensor_sections():
    class Frame:
        frame_number = 7
        mmwave_frame = type("MMW", (), {"points": [1]})()
        presence_frame = type("PRS", (), {"presence_raw": 0.4, "motion_raw": 0.1, "distance_m": 1.2})()
        thermal_frame_bgr = type("THM", (), {"shape": (240, 320, 3)})()

    text = summarize_frame(Frame())
    assert "frame=7" in text
    assert "mmw=on" in text
    assert "ifx=on" in text
    assert "thermal=on" in text


def test_run_loop_stops_at_max_frames():
    hub = _FakeHub()
    lines = []

    frames = run_loop(
        hub,
        max_frames=3,
        interval_s=0.0,
        mmwave_timeout_ms=100,
        printer=lines.append,
        sleeper=lambda _: None,
    )
    assert frames == 3
    assert len(lines) == 3
    assert "frame=1" in lines[0]
