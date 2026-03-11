# Layer 3: Feature Representation

## Objective
Build compact and deterministic feature vectors from the processed output of Layer 2.

## Inputs
- `ProcessedFrame` from Layer 2.

## Outputs
- `FeatureBatch(frame_number, timestamp_ms, vector)`.

## `.py` Files
- `feature_extractor.py`: extracts statistics from `range_doppler` and `point_cloud` size.

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