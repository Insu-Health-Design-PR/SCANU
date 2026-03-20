"""Typed data contracts for 60 GHz presence radar ingestion."""

from __future__ import annotations

from dataclasses import dataclass


BGT60LTR11AIP_SENSOR_MODEL = "BGT60LTR11AIP"
DEMOBGT60LTR11AIPTOBO1_BOARD_KIT = "DEMOBGT60LTR11AIPTOBO1"


@dataclass(frozen=True, slots=True)
class PresenceSample:
    """Raw sample emitted by a BGT60LTR11AIP-compatible provider."""

    presence_raw: float
    motion_raw: float
    distance_m: float
    signal_quality: float = 1.0
    temperature_c: float | None = None
    sensor_model: str = BGT60LTR11AIP_SENSOR_MODEL
    board_kit: str = DEMOBGT60LTR11AIPTOBO1_BOARD_KIT


@dataclass(frozen=True, slots=True)
class PresenceFrame:
    """One raw presence reading from the 60 GHz sensor source."""

    frame_number: int
    timestamp_ms: float
    presence_raw: float
    motion_raw: float
    distance_m: float
    signal_quality: float = 1.0
    temperature_c: float | None = None
    sensor_model: str = BGT60LTR11AIP_SENSOR_MODEL
    board_kit: str = DEMOBGT60LTR11AIPTOBO1_BOARD_KIT


@dataclass(frozen=True, slots=True)
class PresenceFeatures:
    """Normalized presence feature set for downstream fusion."""

    frame_number: int
    timestamp_ms: float
    presence_score: float
    motion_score: float
    confidence: float
    is_present: bool
    distance_m: float
    signal_quality: float
    sensor_model: str = BGT60LTR11AIP_SENSOR_MODEL
    board_kit: str = DEMOBGT60LTR11AIPTOBO1_BOARD_KIT
