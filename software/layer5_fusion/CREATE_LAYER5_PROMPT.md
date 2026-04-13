# Prompt To Implement Layer 5

Use this prompt to implement `Layer 5: Sensor Fusion` in this repository.

## Prompt

You are working inside the SCANU repository.

Implement `Layer 5: Sensor Fusion` under:

`software/layer5_fusion`

Your goal is to create a small, deterministic, typed fusion layer that combines:

- the anomaly/model signal from the main radar pipeline
- auxiliary trigger signals from non-primary sensors

The implementation must fit the architecture already present in this repo.

## Existing Context

Primary radar path:

- `software/layer1_radar`
- `software/layer2_signal_processing`

Auxiliary Layer 1 sensors:

- `software/layer1_sensors_unified/aux_sensors`
- `software/layer1_sensors_unified/thermal_camera`
- `software/layer1_sensors_unified/radar_presence_60g`

Design-only downstream layers:

- `software/layer3_features/LAYER3.md`
- `software/layer4_inference/LAYER4.md`
- `software/layer5_fusion/LAYER5.md`
- `software/layer6_state_machine/LAYER6.md`

Important real contracts already available in the repo:

- `software.layer2_signal_processing.signal_processor.ProcessedFrame`
- `software.layer2_signal_processing.feature_extractor.HeatmapFeatures`
- `software.layer1_sensors_unified.aux_sensors.sensor_models.AuxFrame`
- `software.layer1_sensors_unified.thermal_camera.camera_models.ThermalFeatures`
- `software.layer1_sensors_unified.radar_presence_60g.presence_models.PresenceFeatures`

## Design Requirements

Implement Layer 5 as a fusion layer for already-normalized signals.

Do not:

- read serial ports
- parse raw JSON lines
- perform FFT or heavy signal processing
- implement the state machine
- implement alerts or UI logic

Do:

- accept already-processed scores/features
- normalize missing/optional sources safely
- compute a deterministic `fused_score`
- expose typed outputs with traceable evidence

## Files To Create

Create:

- `software/layer5_fusion/__init__.py`
- `software/layer5_fusion/sensor_fusion.py`

If needed, you may also add:

- `software/layer5_fusion/test_sensor_fusion.py`

Keep the implementation compact and production-friendly.

## Required API

Implement these typed contracts:

1. `FusionInputs`

Suggested fields:

- `frame_number: int`
- `timestamp_ms: float`
- `model_score: float | None = None`
- `model_confidence: float | None = None`
- `thermal_presence_score: float | None = None`
- `thermal_confidence: float | None = None`
- `presence_60g_score: float | None = None`
- `presence_60g_confidence: float | None = None`
- `pir_motion_score: float | None = None`
- `aux_trigger_score: float | None = None`
- `has_fault: bool = False`

2. `FusionResult`

Required fields:

- `frame_number: int`
- `timestamp_ms: float`
- `fused_score: float`
- `confidence: float`
- `evidence: dict[str, float]`
- `missing_sources: tuple[str, ...]`

3. `SensorFusion`

Required behavior:

- configurable weights
- robust handling of missing sources
- output score normalized to `[0.0, 1.0]`
- deterministic result

## Fusion Rules

Implement a weighted fusion strategy.

Suggested sources:

- model score
- thermal presence score
- 60 GHz presence score
- PIR motion / auxiliary trigger score

Rules:

1. Clamp every numeric score to `[0.0, 1.0]`.
2. Ignore sources that are `None`.
3. Renormalize by the sum of the weights of available sources.
4. If no sources are available, return `fused_score = 0.0` and `confidence = 0.0`.
5. If `has_fault` is `True`, keep the result deterministic and expose that fact in `evidence`.

Suggested confidence behavior:

- base confidence on available confidences when provided
- if a source has no explicit confidence, treat its confidence as `1.0`
- return the weighted average confidence of available sources

## Integration Helpers

To make Layer 5 easy to use, provide helper constructors or classmethods where useful, for example:

- from model output plus `ThermalFeatures`
- from model output plus `PresenceFeatures`
- from `AuxFrame` by mapping selected auxiliary readings into a compact trigger score

Do not over-engineer this. Keep helpers small and obvious.

## Evidence

The `evidence` dictionary should be practical for debugging and later state-machine use.

Include values such as:

- `model_score`
- `thermal_presence_score`
- `presence_60g_score`
- `pir_motion_score`
- `aux_trigger_score`
- `weight_sum`
- `fault_flag`

## Coding Style

- Use dataclasses with type hints
- Keep logic deterministic
- Prefer simple, explicit code over abstractions
- Use NumPy only if truly helpful; plain Python is acceptable here
- Match the style already used in `Layer 2` and unified Layer 1 sensor modules

## Testing Expectations

If you add tests, verify at least:

- fusion with only model score
- fusion with multiple sources
- handling of missing sources
- clamping to `[0, 1]`
- behavior when no sources are available
- behavior when `has_fault=True`

## Deliverable

Return:

1. a short explanation of the design
2. the created files
3. any assumptions made about Layer 3 / Layer 4 contracts

