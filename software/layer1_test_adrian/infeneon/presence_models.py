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

    def to_dict(self) -> dict:
        return {
            "frame_number": self.frame_number,
            "timestamp_ms": self.timestamp_ms,
            "presence_raw": self.presence_raw,
            "motion_raw": self.motion_raw,
            "distance_m": self.distance_m,
        }


@dataclass(frozen=True, slots=True)
class PresenceFeatures:
    """Normalized presence feature set for downstream fusion."""

    frame_number: int
    timestamp_ms: float
    presence_score: float
    confidence: float
    is_present: bool
    distance_m: float

    def to_dict(self) -> dict:
        return {
            "frame_number": self.frame_number,
            "timestamp_ms": self.timestamp_ms,
            "presence_score": self.presence_score,
            "confidence": self.confidence,
            "is_present": self.is_present,
            "distance_m": self.distance_m,
        }
