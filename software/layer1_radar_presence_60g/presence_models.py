"""Typed data contracts for 60 GHz presence radar ingestion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PresenceFrame:
    """One raw presence reading from the 60 GHz sensor source."""

    frame_number: int
    timestamp_ms: float
    presence_raw: float
    motion_raw: float
    distance_m: float


@dataclass(frozen=True, slots=True)
class PresenceFeatures:
    """Normalized presence feature set for downstream fusion."""

    frame_number: int
    timestamp_ms: float
    presence_score: float
    confidence: float
    is_present: bool
    distance_m: float
