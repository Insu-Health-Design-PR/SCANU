# Layer 2: Signal Processing

## Objective
Transform raw radar frames from Layer 1 into calibrated spectral outputs and heatmap-ready features.

## Inputs
- `RadarFrame(frame_number, timestamp_ms, payload)` from Layer 1.

## Outputs
- `ProcessedFrame(frame_number, timestamp_ms, range_doppler, point_cloud)`.
- `HeatmapFeatures(frame_number, timestamp_ms, range_heatmap, doppler_heatmap, vector)`.

## Python Files
- `frame_buffer.py`: fixed-size ring buffer for `RadarFrame` objects.
- `calibration.py`: exponential moving background subtraction.
- `signal_processor.py`: FFT + CFAR processing and sparse detection point cloud extraction.
- `feature_extractor.py`: range and doppler heatmap projections plus summary vector.
- `mockdata.py`: deterministic synthetic frame generators for smoke and integration tests.
- `test_parser.py`: parser unit tests (Layer 1 parser coverage driven by Layer 2 task scope).
- `__init__.py`: public API exports.

## Recommended Flow
1. Layer 1 emits `RadarFrame` objects.
2. Optionally cache a temporal window with `FrameBuffer`.
3. `SignalProcessor.process()` runs calibration, range-doppler FFT, then CFAR thresholding.
4. Processor emits a typed `ProcessedFrame`.
5. `FeatureExtractor.extract()` builds heatmaps and vector features for downstream inference.

## Definition of Done (DoD)
- Typed and documented APIs.
- Deterministic behavior with lightweight numerical operations.
- Parser unit tests runnable from Layer 2 task context.
- End-to-end compatibility with downstream feature consumers.
