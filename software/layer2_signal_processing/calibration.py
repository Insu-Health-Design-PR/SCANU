"""Background model used for simple calibration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class BackgroundModel:
    """Exponential moving baseline subtraction model."""

    alpha: float = 0.05
    baseline: np.ndarray | None = None

    def update(self, sample: np.ndarray) -> np.ndarray:
        sample_arr = np.asarray(sample, dtype=np.float32)

        # Reset baseline when shape changes to keep calibration safe and deterministic.
        if self.baseline is None or self.baseline.shape != sample_arr.shape:
            self.baseline = sample_arr.copy()
        else:
            self.baseline = (1.0 - self.alpha) * self.baseline + self.alpha * sample_arr
        return self.baseline

    def subtract(self, sample: np.ndarray) -> np.ndarray:
        sample_arr = np.asarray(sample, dtype=np.float32)
        if self.baseline is None or self.baseline.shape != sample_arr.shape:
            return sample_arr
        return sample_arr - self.baseline
