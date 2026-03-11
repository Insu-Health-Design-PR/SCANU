# Layer 2: Signal Processing

## Objective
Transform raw radar frames from Layer 1 into a stable, calibrated numeric representation for feature extraction.

## Inputs
- `RadarFrame(frame_number, timestamp_ms, payload)` from Layer 1.

## Outputs
- `ProcessedFrame(frame_number, timestamp_ms, range_doppler, point_cloud)`.

## Python Files
- `frame_buffer.py`: fixed-size temporal window for `RadarFrame` objects.
- `calibration.py`: `BackgroundModel` with exponential moving baseline.
- `signal_processor.py`: deterministic pipeline from payload bytes to calibrated tensors.
- `mockdata.py`: deterministic synthetic frame generators for integration and smoke tests.
- `__init__.py`: public exports.

## Recommended Flow
1. Layer 1 emits `RadarFrame` objects.
2. Optionally accumulate recent frames with `FrameBuffer`.
3. `SignalProcessor.process()` converts payload bytes to float magnitudes.
4. `BackgroundModel` updates baseline and performs subtraction.
5. `SignalProcessor` emits `ProcessedFrame` with 2D `range_doppler` and typed `point_cloud` (`N x 3`).
6. Layer 3 consumes `ProcessedFrame` directly.

## Definition of Done (DoD)
- Typed, documented, importable API.
- Deterministic behavior without hardware dependencies.
- Output contract is directly consumable by Layer 3.
- Includes deterministic mock data helpers for test setup.
