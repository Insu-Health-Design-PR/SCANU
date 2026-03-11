"""Deterministic mock data helpers for Layer 2 integration tests."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .frame_buffer import RadarFrame
from .signal_processor import ProcessedFrame, SignalProcessor


@dataclass(frozen=True, slots=True)
class MockFrameSpec:
    """Configuration for synthetic radar frame generation."""

    frame_number: int = 1
    timestamp_ms: float = 0.0
    sample_count: int = 64


def build_mock_radar_frame(spec: MockFrameSpec = MockFrameSpec()) -> RadarFrame:
    """Builds one deterministic frame with a repeatable waveform payload."""
    t = np.arange(spec.sample_count, dtype=np.float32)
    waveform = (np.sin(0.18 * t) + 1.0) * 90.0
    payload = np.clip(waveform, 0, 255).astype(np.uint8).tobytes()
    return RadarFrame(
        frame_number=spec.frame_number,
        timestamp_ms=spec.timestamp_ms,
        payload=payload,
    )


def build_mock_sequence(count: int = 4, sample_count: int = 64) -> list[RadarFrame]:
    """Builds a deterministic sequence of radar frames."""
    if count <= 0:
        return []
    return [
        build_mock_radar_frame(
            MockFrameSpec(
                frame_number=i + 1,
                timestamp_ms=float(i * 100.0),
                sample_count=sample_count,
            )
        )
        for i in range(count)
    ]


def build_mock_processed_frame(processor: SignalProcessor | None = None) -> ProcessedFrame:
    """Returns one `ProcessedFrame` in the exact contract expected by Layer 3."""
    engine = processor if processor is not None else SignalProcessor()
    frame = build_mock_radar_frame()
    return engine.process(frame)
