# Layer 1 - 60 GHz Presence Radar

## Objective
Acquire and normalize presence radar signals from the Infineon `DEMOBGT60LTR11AIPTOBO1` board for downstream fusion.

## Inputs
- Presence radar samples from a provider (`presence_raw`, `motion_raw`, `distance_m`).

## Outputs
- `PresenceFrame` (raw, typed sample frame).
- `PresenceFeatures` (normalized score, confidence, binary presence flag).

## Files
- `presence_models.py`: typed frame/feature contracts.
- `presence_source.py`: provider protocol, mock provider, and source adapter.
- `presence_processor.py`: deterministic normalization and thresholding.
- `__init__.py`: public API exports.
- `test_presence_source.py`: source/provider test.
- `test_presence_processor.py`: processor test.

## Recommended Flow
1. Create `PresenceSource` with a provider.
2. Read `PresenceFrame` objects.
3. Convert to `PresenceFeatures` with `PresenceProcessor.extract()`.
4. Feed `presence_score`, `confidence`, and `is_present` into Layer 5 fusion.

## DoD
- Typed contracts and deterministic behavior.
- Mock provider available for hardware-free smoke tests.
- Unit tests cover source and processor behavior.
