# Layer 1 - 60 GHz Presence Radar

## Objective
Acquire and normalize presence radar signals from the Infineon XENSIV `BGT60LTR11AIP` sensor on the `DEMOBGT60LTR11AIPTOBO1` development kit for downstream fusion.

## Inputs
- Presence radar samples from a provider (`presence_raw`, `motion_raw`, `distance_m`).
- Optional sensor metadata and signal quality from the provider (`signal_quality`, `temperature_c`, board/sensor identifiers).

## Outputs
- `PresenceFrame` (raw, typed sample frame).
- `PresenceFeatures` (normalized score, motion score, confidence, binary presence flag).

## Files
- `presence_models.py`: typed sample/frame/feature contracts and kit constants.
- `presence_source.py`: provider protocol, mock provider, serial provider, and source adapter.
- `presence_processor.py`: deterministic normalization and confidence weighting.
- `__init__.py`: public API exports.
- `test_presence_source.py`: source/provider test.
- `test_presence_processor.py`: processor test.

## Recommended Flow
1. Create `PresenceSource` with a provider.
2. For hardware, use `BGT60LTR11AIPSerialProvider` and let it autodetect the Infineon/XENSIV serial port or pass one explicitly.
3. Read `PresenceFrame` objects.
4. Convert to `PresenceFeatures` with `PresenceProcessor.extract()`.
5. Feed `presence_score`, `motion_score`, `confidence`, and `is_present` into Layer 5 fusion.

## DoD
- Typed contracts and deterministic behavior.
- Mock provider available for hardware-free smoke tests.
- Unit tests cover source and processor behavior.
