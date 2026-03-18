"""Feature extraction contracts for Layer 3."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from software.layer2_signal_processing import ProcessedFrame


@dataclass(frozen=True, slots=True)
class FeatureBatch:
    """Compact feature vector generated from one processed frame."""

    frame_number: int
    timestamp_ms: float
    vector: np.ndarray


class FeatureExtractor:
    """Builds deterministic feature vectors from Layer 2 outputs."""

    def extract(self, processed: ProcessedFrame) -> FeatureBatch:
        rd = np.asarray(processed.range_doppler, dtype=np.float32)
        if rd.size == 0:
            stats = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        else:
            stats = np.array(
                [
                    float(np.mean(rd)),
                    float(np.std(rd)),
                    float(np.max(rd)),
                    float(np.min(rd)),
                ],
                dtype=np.float32,
            )
        point_count = np.array([float(processed.point_cloud.shape[0])], dtype=np.float32)
        vector = np.concatenate((stats, point_count), dtype=np.float32)
        return FeatureBatch(
            frame_number=processed.frame_number,
            timestamp_ms=processed.timestamp_ms,
            vector=vector,
        )
