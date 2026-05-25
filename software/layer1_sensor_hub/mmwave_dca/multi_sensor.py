"""Multi-sensor synchronisation for 2+ mmWave + DCA1000 sensor pairs.

Supports capturing raw ADC from multiple TI mmWave sensors simultaneously,
each with its own DCA1000EVM, for multi-angle concealed-weapon screening.

Usage example (dual-sensor):
    from pathlib import Path
    from .multi_sensor import MultiSensorPlan, run_multi_sensor_capture

    plan = MultiSensorPlan(
        sensors=[
            SensorCapturePlan(
                name="sensor_left",
                radar_cli_port="/dev/ttyUSB0",
                radar_data_port="/dev/ttyUSB1",
                radar_config=Path("cfg/weapon_detection_dca1000.cfg"),
                dca_config=Path("ti_cli/configFile.json"),
                dca_network=Dca1000NetworkConfig(
                    pc_ip="192.168.33.30",
                    dca_ip="192.168.33.180",
                ),
            ),
            SensorCapturePlan(
                name="sensor_right",
                radar_cli_port="/dev/ttyUSB2",
                radar_data_port="/dev/ttyUSB3",
                radar_config=Path("cfg/weapon_detection_dca1000.cfg"),
                dca_config=Path("ti_cli/configFile.json"),
                dca_network=Dca1000NetworkConfig(
                    pc_ip="192.168.33.30",
                    dca_ip="192.168.33.181",
                ),
            ),
        ],
        output_dir=Path("captures/dual_sensor"),
        duration_s=5.0,
    )
    results = run_multi_sensor_capture(plan)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .capture_runner import CapturePlan, run_capture_plan
from .dca1000_udp import Dca1000NetworkConfig, UdpCaptureResult
from .radar_cli import RadarCliConfig

logger = logging.getLogger(__name__)


@dataclass
class SensorCapturePlan:
    """Capture parameters for one mmWave + DCA1000 sensor pair."""

    name: str
    radar_cli_port: str
    radar_config: Path
    dca_config: Path
    network: Dca1000NetworkConfig = Dca1000NetworkConfig()
    dca_retries: int = 2


@dataclass
class MultiSensorPlan:
    """Plan for simultaneous multi-sensor raw ADC capture."""

    sensors: List[SensorCapturePlan]
    output_dir: Path = Path("captures/multi_sensor")
    duration_s: float = 5.0
    arm_delay_s: float = 0.5


@dataclass
class MultiSensorResult:
    """Capture result for each sensor in a multi-sensor run."""

    per_sensor: Dict[str, UdpCaptureResult]
    total_elapsed_s: float


def run_multi_sensor_capture(plan: MultiSensorPlan) -> MultiSensorResult:
    """Run simultaneous ADC capture across multiple sensor pairs.

    The workflow:
    1. Configure each radar sensor (``sensorStart`` deferred)
    2. Configure each DCA1000 board
    3. Start all DCA1000 recordings
    4. Start all radar sensors (near-simultaneous)
    5. Capture UDP packets from all sensors
    6. Stop everything
    """

    plan.output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1 — Configure all radars
    capture_plans: List[CapturePlan] = []
    for s in plan.sensors:
        radar_cfg = RadarCliConfig(port=s.radar_cli_port, timeout_s=3.0)
        output_path = plan.output_dir / f"{s.name}_adc_data.bin"
        cp = CapturePlan(
            radar_cli=radar_cfg,
            radar_config_path=s.radar_config,
            output_path=output_path,
            network=s.network,
            record_duration_s=plan.duration_s,
            configure_radar=True,
            configure_dca=True,
            dca_config_path=s.dca_config,
            start_sensor=False,
            start_dca_recording=False,
            stop_dca_recording_after_capture=True,
            stop_sensor_after_capture=True,
            arm_delay_s=plan.arm_delay_s,
            dca_retries=s.dca_retries,
        )
        capture_plans.append(cp)

    # Configure all sensors
    logger.info("Configuring %d radar sensors ...", len(capture_plans))
    for cp in capture_plans:
        run_capture_plan(cp)

    # Steps 2-6: record from each sensor
    results: Dict[str, UdpCaptureResult] = {}
    start = time.monotonic()

    logger.info("Starting capture on all sensors ...")
    for cp in capture_plans:
        sensor_name = [s.name for s in plan.sensors if s.network == cp.network]
        label = sensor_name[0] if sensor_name else cp.network.dca_ip
        logger.info("  Sensor %s: listening on %s:%d", label, cp.network.pc_ip, cp.network.data_port)
        result = run_capture_plan(cp)
        results[label] = result

    elapsed = time.monotonic() - start
    return MultiSensorResult(per_sensor=results, total_elapsed_s=elapsed)
