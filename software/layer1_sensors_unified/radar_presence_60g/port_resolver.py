"""Infineon 60 GHz presence radar serial port resolver."""

from __future__ import annotations

from software.layer1_sensors_unified.common import PortInfo, PortScanner


class Presence60GPortResolver:
    """Finds likely Infineon USB/UART ports for 60 GHz presence boards."""

    KEYWORDS = (
        "infineon",
        "bgt60",
        "bgt60ltr11",
        "bgt60ltr11aip",
        "demobgt60ltr11aiptobo1",
        "xensiv",
        "radar presence",
    )

    @staticmethod
    def find_candidates(ports: tuple[PortInfo, ...] | None = None) -> tuple[PortInfo, ...]:
        known = ports if ports is not None else PortScanner.scan()
        scored_matches: list[tuple[int, PortInfo]] = []
        for port in known:
            text = f"{port.description} {port.manufacturer} {port.hwid}".lower()
            score = sum(1 for keyword in Presence60GPortResolver.KEYWORDS if keyword in text)
            if score:
                scored_matches.append((score, port))
        scored_matches.sort(key=lambda item: (-item[0], item[1].device))
        return tuple(port for _, port in scored_matches)
