# Layer 3: Feature Representation

## Objective
Build compact and deterministic feature vectors from the processed output of Layer 2.

## Inputs
- `ProcessedFrame` from Layer 2.

## Outputs
- `FeatureBatch(frame_number, timestamp_ms, vector)`.

## `.py` Files
- `dataset.py`: groups `*_capture.json`, `*_report.json`, and `.mp4` under `safe/<scenario>/` and `unsafe/<scenario>/`; builds per-frame numpy feature matrices from rich capture JSON (for fusion / sequence models). See `CAPTURE_FRAME_FEATURE_NAMES`.

- `visualizer.py`: plots Layer 2–style feature JSON (legacy path).

- `__init__.py`: public exports.

## Recommended Flow
1. Receive `ProcessedFrame`.

2. Calculate statistics (`mean`, `std`, `max`, `min`) from `range_doppler`.

3. Add point count from `point_cloud`.

4. Deliver `FeatureBatch` to Layer 4.

## Exit Criteria (DoD)
- Typed numeric vector (`np.ndarray`) with stable form.

- Reproducible result with the same input.

- Direct integration with `InferenceEngine`.