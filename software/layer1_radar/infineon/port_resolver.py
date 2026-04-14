"""Infineon 60 GHz presence radar serial port resolver."""

from __future__ import annotations

from .common_ports import PortInfo, PortScanner


class Presence60GPortResolver:
    """Finds likely Infineon USB/UART ports for 60 GHz presence boards."""

    KEYWORDS = (
        "infineon",
        "bgt60",
        "radar presence",
    )

    @staticmethod
    def find_candidates(ports: tuple[PortInfo, ...] | None = None) -> tuple[PortInfo, ...]:
        known = ports if ports is not None else PortScanner.scan()
        matches: list[PortInfo] = []
        for port in known:
            text = f"{port.description} {port.manufacturer} {port.hwid}".lower()
            if any(k in text for k in Presence60GPortResolver.KEYWORDS):
                matches.append(port)
        return tuple(matches)

