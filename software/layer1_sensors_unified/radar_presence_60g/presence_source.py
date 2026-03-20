"""Source adapters for 60 GHz presence radar data."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Protocol

from .presence_models import PresenceFrame, PresenceSample
from .port_resolver import Presence60GPortResolver


class PresenceProvider(Protocol):
    """Provider contract for a presence reading source."""

    def read_sample(self) -> tuple[float, float, float] | PresenceSample:
        """Returns a legacy tuple or a structured `PresenceSample`."""


class MockPresenceProvider:
    """Deterministic mock provider for development and smoke testing."""

    def __init__(self) -> None:
        self._counter = 0

    def read_sample(self) -> PresenceSample:
        self._counter += 1
        cycle = self._counter % 6
        if cycle in (0, 1):
            return PresenceSample(0.15, 0.10, 2.8, signal_quality=0.80, temperature_c=29.0)
        if cycle in (2, 3):
            return PresenceSample(0.55, 0.45, 1.9, signal_quality=0.92, temperature_c=29.4)
        return PresenceSample(0.85, 0.70, 1.2, signal_quality=0.98, temperature_c=29.8)


@dataclass(frozen=True, slots=True)
class BGT60LTR11AIPSerialConfig:
    """Runtime serial settings for the Infineon XENSIV BGT60LTR11AIP dev kit."""

    port: str | None = None
    baudrate: int = 115200
    timeout_s: float = 1.0
    max_line_bytes: int = 512


@dataclass(slots=True)
class _NullSerial:
    """Fallback placeholder when serial module is unavailable."""

    is_open: bool = False


class BGT60LTR11AIPSerialProvider:
    """
    Reads presence samples from a serial terminal exposed by the BGT60LTR11AIP kit.

    Supported line formats include:
    - JSON, e.g. `{"presence": 1, "motion": 0.42, "distance_m": 1.7}`
    - key/value text, e.g. `presence=1 motion=0.42 distance=1.7 quality=0.9`
    - terminal status lines, e.g. `Presence detected, direction=approaching`
    """

    _NUMBER_RE = re.compile(r"(?P<key>[a-zA-Z_]+)\s*[:=]\s*(?P<value>-?\d+(?:\.\d+)?)")
    _DIRECTION_GAIN = {
        "approaching": 0.85,
        "moving": 0.75,
        "receding": 0.65,
        "departing": 0.65,
        "stationary": 0.35,
        "still": 0.20,
    }

    def __init__(
        self,
        config: BGT60LTR11AIPSerialConfig | None = None,
        serial_port: object | None = None,
    ) -> None:
        self.config = config or BGT60LTR11AIPSerialConfig()
        self._port = serial_port

    def connect(self) -> None:
        if self._port is not None and getattr(self._port, "is_open", False):
            return

        try:
            import serial  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on env
            raise RuntimeError(
                "pyserial is required for BGT60LTR11AIPSerialProvider.connect()"
            ) from exc

        port_name = self.config.port or self._autodetect_port()
        self._port = serial.Serial(
            port=port_name,
            baudrate=self.config.baudrate,
            timeout=self.config.timeout_s,
        )

    def disconnect(self) -> None:
        if self._port is not None and getattr(self._port, "is_open", False):
            self._port.close()
        self._port = None

    @property
    def is_connected(self) -> bool:
        return self._port is not None and bool(getattr(self._port, "is_open", False))

    def read_sample(self) -> PresenceSample:
        if not self.is_connected:
            self.connect()

        while True:
            raw = self._port.readline(self.config.max_line_bytes)
            if not raw:
                raise TimeoutError(
                    "Timed out waiting for BGT60LTR11AIP serial output"
                )

            line = raw.decode("utf-8", errors="ignore").strip()
            sample = self.parse_line(line)
            if sample is not None:
                return sample

    def parse_line(self, line: str) -> PresenceSample | None:
        text = line.strip()
        if not text:
            return None

        parsed = self._parse_json_line(text)
        if parsed is not None:
            return parsed

        parsed = self._parse_key_value_line(text)
        if parsed is not None:
            return parsed

        parsed = self._parse_status_line(text)
        if parsed is not None:
            return parsed

        return None

    def _autodetect_port(self) -> str:
        candidates = Presence60GPortResolver.find_candidates()
        if not candidates:
            raise RuntimeError(
                "Could not find a BGT60LTR11AIP serial port automatically"
            )
        return candidates[0].device

    def _parse_json_line(self, text: str) -> PresenceSample | None:
        if not text.startswith("{"):
            return None

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return self._sample_from_mapping(payload)

    def _parse_key_value_line(self, text: str) -> PresenceSample | None:
        values = {
            match.group("key").lower(): float(match.group("value"))
            for match in self._NUMBER_RE.finditer(text)
        }
        if not values:
            return None

        lowered = text.lower()
        if "presence" in lowered and "detected" in lowered and "presence" not in values:
            values["presence"] = 1.0
        return self._sample_from_mapping(values)

    def _parse_status_line(self, text: str) -> PresenceSample | None:
        lowered = text.lower()
        if "presence" not in lowered:
            return None

        present = 1.0 if "detected" in lowered or "present" in lowered else 0.0
        motion = 0.0
        for direction, score in self._DIRECTION_GAIN.items():
            if direction in lowered:
                motion = score
                break
        quality = 0.85 if present else 0.60
        return PresenceSample(
            presence_raw=present,
            motion_raw=motion,
            distance_m=-1.0,
            signal_quality=quality,
        )

    def _sample_from_mapping(self, payload: dict[str, object]) -> PresenceSample:
        def _float(*keys: str, default: float) -> float:
            for key in keys:
                if key in payload and payload[key] is not None:
                    return float(payload[key])  # type: ignore[arg-type]
            return default

        presence = _float("presence_raw", "presence", "target_presence", default=0.0)
        motion = _float("motion_raw", "motion", "speed", default=presence)
        distance = _float("distance_m", "distance", "range_m", default=-1.0)
        quality = _float("signal_quality", "quality", "confidence", default=1.0)
        temperature_raw = payload.get("temperature_c")
        temperature = float(temperature_raw) if temperature_raw is not None else None

        return PresenceSample(
            presence_raw=presence,
            motion_raw=motion,
            distance_m=distance,
            signal_quality=quality,
            temperature_c=temperature,
        )


class PresenceSource:
    """Reads sequential presence frames from a provider."""

    def __init__(self, provider: PresenceProvider) -> None:
        self._provider = provider
        self._frame_number = 0

    def read_frame(self) -> PresenceFrame:
        self._frame_number += 1
        sample = self._provider.read_sample()
        if isinstance(sample, PresenceSample):
            normalized = sample
        else:
            presence_raw, motion_raw, distance_m = sample
            normalized = PresenceSample(
                presence_raw=float(presence_raw),
                motion_raw=float(motion_raw),
                distance_m=float(distance_m),
            )
        return PresenceFrame(
            frame_number=self._frame_number,
            timestamp_ms=time.time() * 1000.0,
            presence_raw=float(normalized.presence_raw),
            motion_raw=float(normalized.motion_raw),
            distance_m=float(normalized.distance_m),
            signal_quality=float(normalized.signal_quality),
            temperature_c=normalized.temperature_c,
            sensor_model=normalized.sensor_model,
            board_kit=normalized.board_kit,
        )
