"""Local serial port scanner helpers for Infineon integrations.

This avoids importing `software.layer1_sensors_unified` (which pulls in other
modules at import time) and keeps this package self-contained.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class PortInfo:
    device: str
    description: str
    manufacturer: str
    vid: int | None
    pid: int | None
    hwid: str


class PortScanner:
    @staticmethod
    def scan(records: Iterable[object] | None = None) -> tuple[PortInfo, ...]:
        if records is None:
            records = PortScanner._read_system_ports()

        items: list[PortInfo] = []
        for port in records:
            items.append(
                PortInfo(
                    device=str(getattr(port, "device", "")),
                    description=str(getattr(port, "description", "")),
                    manufacturer=str(getattr(port, "manufacturer", "")),
                    vid=getattr(port, "vid", None),
                    pid=getattr(port, "pid", None),
                    hwid=str(getattr(port, "hwid", "")),
                )
            )
        return tuple(items)

    @staticmethod
    def _read_system_ports() -> Iterable[object]:
        try:
            import serial.tools.list_ports  # type: ignore
        except ImportError:
            return ()
        return serial.tools.list_ports.comports()
