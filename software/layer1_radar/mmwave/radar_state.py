"""
Radar state inspection and recovery helpers for TI mmWave UART setup.

This module focuses on *radar-side* state (CLI responsiveness + DATA stream
health), not OS-level process ownership checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time

from .radar_constants import MAGIC_WORD
from .serial_manager import SerialManager


class CliState(str, Enum):
    DISCONNECTED = "disconnected"
    NO_RESPONSE = "no_response"
    RESPONDS_NO_PROMPT = "responds_no_prompt"
    PROMPT_READY = "prompt_ready"


class DataState(str, Enum):
    DISCONNECTED = "disconnected"
    NO_BYTES = "no_bytes"
    BYTES_NO_MAGIC = "bytes_no_magic"
    STREAMING_FRAMES = "streaming_frames"


class RadarState(str, Enum):
    DISCONNECTED = "disconnected"
    CLI_DOWN = "cli_down"
    IDLE_STOPPED = "idle_stopped"
    STREAMING_OK = "streaming_ok"
    STREAM_WEDGED = "stream_wedged"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CliProbe:
    state: CliState
    response_text: str
    command_used: str


@dataclass(frozen=True, slots=True)
class DataProbe:
    state: DataState
    bytes_seen: int
    magic_hits: int
    sample_window_s: float


@dataclass(frozen=True, slots=True)
class RadarStateReport:
    radar_state: RadarState
    cli: CliProbe
    data: DataProbe
    summary: str


class RadarStateInspector:
    """
    Inspect and recover radar stream state using existing opened UART ports.

    Requirements:
    - `SerialManager.connect(...)` must already be called.
    """

    def __init__(self, serial_mgr: SerialManager):
        self.serial = serial_mgr

    def _probe_cli(self, timeout_s: float = 1.0) -> CliProbe:
        port = self.serial.config_port
        if port is None or not port.is_open:
            return CliProbe(CliState.DISCONNECTED, "", "")

        # Commands ordered from non-invasive to slightly more stateful.
        candidates = ("version", "help", "sensorStop")
        for cmd in candidates:
            text = self.serial.send_cli_command(cmd, timeout_s=timeout_s)
            cleaned = (text or "").strip()
            if cleaned:
                has_prompt = ("mmwDemo:/>" in cleaned) or cleaned.endswith(">")
                state = CliState.PROMPT_READY if has_prompt else CliState.RESPONDS_NO_PROMPT
                return CliProbe(state, cleaned, cmd)

        return CliProbe(CliState.NO_RESPONSE, "", candidates[-1])

    def _probe_data(self, window_s: float = 0.35, poll_s: float = 0.01) -> DataProbe:
        port = self.serial.data_port
        if port is None or not port.is_open:
            return DataProbe(DataState.DISCONNECTED, 0, 0, window_s)

        end_t = time.time() + max(window_s, 0.05)
        bytes_seen = 0
        magic_hits = 0
        rolling = bytearray()

        while time.time() < end_t:
            waiting = port.in_waiting
            if waiting > 0:
                data = port.read(waiting)
                bytes_seen += len(data)
                rolling.extend(data)
                if len(rolling) > 8192:
                    del rolling[:-8192]
                magic_hits += rolling.count(MAGIC_WORD)
            else:
                time.sleep(max(poll_s, 0.002))

        if bytes_seen == 0:
            state = DataState.NO_BYTES
        elif magic_hits == 0:
            state = DataState.BYTES_NO_MAGIC
        else:
            state = DataState.STREAMING_FRAMES

        return DataProbe(state, bytes_seen, magic_hits, window_s)

    def inspect(self, cli_timeout_s: float = 1.0, data_window_s: float = 0.35) -> RadarStateReport:
        cli = self._probe_cli(timeout_s=cli_timeout_s)
        data = self._probe_data(window_s=data_window_s)

        if cli.state == CliState.DISCONNECTED or data.state == DataState.DISCONNECTED:
            radar_state = RadarState.DISCONNECTED
        elif cli.state == CliState.NO_RESPONSE:
            radar_state = RadarState.CLI_DOWN
        elif data.state == DataState.STREAMING_FRAMES:
            radar_state = RadarState.STREAMING_OK
        elif data.state == DataState.NO_BYTES and cli.state in (CliState.PROMPT_READY, CliState.RESPONDS_NO_PROMPT):
            radar_state = RadarState.IDLE_STOPPED
        elif data.state in (DataState.NO_BYTES, DataState.BYTES_NO_MAGIC):
            radar_state = RadarState.STREAM_WEDGED
        else:
            radar_state = RadarState.UNKNOWN

        summary = (
            f"state={radar_state.value} "
            f"cli={cli.state.value}({cli.command_used or 'n/a'}) "
            f"data={data.state.value} bytes={data.bytes_seen} magic={data.magic_hits}"
        )
        return RadarStateReport(radar_state=radar_state, cli=cli, data=data, summary=summary)

    def recover_stream(self, start_after_stop: bool = True) -> RadarStateReport:
        """
        Attempt a radar-side recovery sequence for wedged stream conditions.

        Sequence:
        1) Probe current state.
        2) If CLI responds, issue `sensorStop`.
        3) Flush stale DATA bytes.
        4) Optionally issue `sensorStart`.
        5) Re-probe and return final state report.
        """
        before = self.inspect()
        if before.cli.state in (CliState.PROMPT_READY, CliState.RESPONDS_NO_PROMPT):
            self.serial.send_cli_command("sensorStop", timeout_s=1.2)
            self.serial.flush_data_port()
            if start_after_stop:
                self.serial.send_cli_command("sensorStart", timeout_s=1.5)
            time.sleep(0.15)
        return self.inspect()

