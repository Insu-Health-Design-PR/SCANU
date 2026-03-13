"""ESP32 auxiliary sensor serial port resolver."""

from __future__ import annotations

from software.layer1_sensors_unified.common import PortInfo, PortScanner


class AuxSensorPortResolver:
    """Finds likely ESP32/USB-UART ports for auxiliary sensors."""

    KEYWORDS = (
        "esp32",
        "cp210",
        "ch340",
        "usb serial",
        "silicon labs",
    )

    @staticmethod
    def find_candidates(ports: tuple[PortInfo, ...] | None = None) -> tuple[PortInfo, ...]:
        known = ports if ports is not None else PortScanner.scan()
        matches: list[PortInfo] = []
        for port in known:
            text = f"{port.description} {port.manufacturer} {port.hwid}".lower()
            if any(k in text for k in AuxSensorPortResolver.KEYWORDS):
                matches.append(port)
        return tuple(matches)
