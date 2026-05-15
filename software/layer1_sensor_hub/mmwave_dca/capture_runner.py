"""High-level runner for radar CLI + DCA1000 UDP raw ADC capture."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .dca1000_udp import Dca1000NetworkConfig, UdpCaptureResult, UdpDca1000Recorder
from .radar_cli import RadarCliConfig, configure_radar_from_file, send_sensor_start, send_sensor_stop


@dataclass(frozen=True, slots=True)
class CapturePlan:
    """One raw ADC capture run."""

    radar_cli: RadarCliConfig
    radar_config_path: Path
    output_path: Path
    network: Dca1000NetworkConfig = Dca1000NetworkConfig()
    record_duration_s: Optional[float] = 5.0
    max_packets: int = 0
    configure_radar: bool = True
    start_sensor: bool = True
    stop_sensor_after_capture: bool = True
    arm_delay_s: float = 0.25


def run_capture_plan(plan: CapturePlan) -> UdpCaptureResult:
    """Run one practical lab capture.

    This arms the radar configuration path and listens for DCA1000 UDP data.
    If you use TI's DCA1000 CLI/mmWave Studio to start the board, start it
    before calling this function or while it is waiting for packets.
    """

    if plan.configure_radar:
        configure_radar_from_file(plan.radar_cli, plan.radar_config_path, defer_sensor_start=True)

    time.sleep(plan.arm_delay_s)

    try:
        recorder = UdpDca1000Recorder(plan.network)

        def on_ready() -> None:
            if plan.start_sensor:
                send_sensor_start(plan.radar_cli)

        return recorder.capture(
            plan.output_path,
            duration_s=plan.record_duration_s,
            max_packets=plan.max_packets,
            on_ready=on_ready,
        )
    finally:
        if plan.stop_sensor_after_capture:
            try:
                send_sensor_stop(plan.radar_cli)
            except Exception:
                pass
