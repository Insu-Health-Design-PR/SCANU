"""High-level runner for radar CLI + DCA1000 UDP raw ADC capture."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .dca1000_control import Dca1000NativeClient, load_dca_config, network_from_config
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
    configure_dca: bool = False
    dca_config_path: Optional[Path] = None
    start_sensor: bool = True
    start_dca_recording: bool = False
    stop_dca_recording_after_capture: bool = False
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

    capture_network = plan.network
    dca_client: Dca1000NativeClient | None = None
    if plan.configure_dca or plan.start_dca_recording or plan.stop_dca_recording_after_capture:
        dca_config = {}
        if plan.dca_config_path is not None:
            dca_config = load_dca_config(plan.dca_config_path)
            capture_network = network_from_config(dca_config)
        dca_client = Dca1000NativeClient(capture_network)
        if plan.configure_dca:
            results = dca_client.configure_from_json(dca_config)
            failed = [r.command for r in results if not r.ok]
            if failed:
                raise RuntimeError(f"DCA1000 configuration failed for commands: {', '.join(failed)}")

    time.sleep(plan.arm_delay_s)

    try:
        recorder = UdpDca1000Recorder(capture_network)

        def on_ready() -> None:
            if dca_client is not None and plan.start_dca_recording:
                result = dca_client.send_command("start")
                if not result.ok:
                    raise RuntimeError(f"DCA1000 start_record failed: {result.response_hex or '<no response>'}")
            if plan.start_sensor:
                send_sensor_start(plan.radar_cli)

        return recorder.capture(
            plan.output_path,
            duration_s=plan.record_duration_s,
            max_packets=plan.max_packets,
            on_ready=on_ready,
        )
    finally:
        if dca_client is not None and plan.stop_dca_recording_after_capture:
            try:
                dca_client.send_command("stop")
            except Exception:
                pass
        if plan.stop_sensor_after_capture:
            try:
                send_sensor_stop(plan.radar_cli)
            except Exception:
                pass
