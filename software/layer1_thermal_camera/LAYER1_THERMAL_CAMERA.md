# Layer 1 - Thermal Camera

## Objective
Acquire thermal frames and extract lightweight thermal presence features for downstream fusion.

## Inputs
- Thermal camera frames from a provider (real hardware adapter or mock provider).

## Outputs
- `ThermalFrame` with temperature map in Celsius.
- `ThermalFeatures` with max/mean temperature, hotspot ratio, and presence score.

## Files
- `camera_models.py`: typed frame/feature dataclasses.
- `camera_source.py`: provider protocol, mock provider, and source orchestrator.
- `camera_processor.py`: deterministic feature extraction.
- `__init__.py`: public exports.

## Recommended Flow
1. Instantiate `ThermalCameraSource` with a provider.
2. Read `ThermalFrame` objects.
3. Process with `ThermalProcessor.extract()`.
4. Feed `presence_score` and thermal metrics into fusion.

## DoD
- Hardware-agnostic source contract.
- Deterministic mock mode for smoke tests.
- Typed outputs ready for Layer 5 fusion.
