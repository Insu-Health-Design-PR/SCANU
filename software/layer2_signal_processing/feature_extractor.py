"""Feature extraction helpers for Layer 2 heatmaps."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .signal_processor import ProcessedFrame


@dataclass(frozen=True, slots=True)
class HeatmapFeatures:
    """Heatmap projections and summary vector derived from one processed frame."""

    frame_number: int
    timestamp_ms: float
    range_heatmap: np.ndarray
    doppler_heatmap: np.ndarray
    vector: np.ndarray


class FeatureExtractor:
    """Builds deterministic heatmap features from a range-doppler map."""

    def extract(self, processed: ProcessedFrame) -> HeatmapFeatures:
        rd = np.asarray(processed.range_doppler, dtype=np.float32)
        if rd.ndim != 2:
            raise ValueError("ProcessedFrame.range_doppler must be 2D")

        range_heatmap = np.sum(rd, axis=1, dtype=np.float32)
        doppler_heatmap = np.sum(rd, axis=0, dtype=np.float32)
        point_count = float(processed.point_cloud.shape[0])

        vector = np.array(
            [
                float(np.mean(rd)),
                float(np.std(rd)),
                float(np.max(rd)),
                float(np.min(rd)),
                point_count,
            ],
            dtype=np.float32,
        )

        return HeatmapFeatures(
            frame_number=processed.frame_number,
            timestamp_ms=processed.timestamp_ms,
            range_heatmap=range_heatmap,
            doppler_heatmap=doppler_heatmap,
            vector=vector,
        )
