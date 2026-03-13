"""Serial transport adapter for ESP32 auxiliary sensor stream."""

from __future__ import annotations

from dataclasses import dataclass

from .config import AuxSerialConfig


@dataclass(slots=True)
class _NullSerial:
    """Fallback placeholder when serial module is unavailable."""

    is_open: bool = False


class SerialBridge:
    """Thin wrapper over pyserial with explicit lifecycle methods."""

    def __init__(self, config: AuxSerialConfig) -> None:
        self.config = config
        self._port: object | None = None

    def connect(self) -> None:
        try:
            import serial  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on env
            raise RuntimeError("pyserial is required for SerialBridge.connect()") from exc

        self._port = serial.Serial(
            port=self.config.port,
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

    def readline(self) -> bytes:
        if not self.is_connected:
            raise RuntimeError("Serial bridge is not connected")

        line = self._port.readline(self.config.max_line_bytes)
        return bytes(line)

    def write_line(self, text: str) -> None:
        if not self.is_connected:
            raise RuntimeError("Serial bridge is not connected")
        payload = (text.rstrip("\n") + "\n").encode("utf-8")
        self._port.write(payload)
