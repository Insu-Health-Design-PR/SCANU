# Layer 5: Sensor Fusion

## Objective
Fuse the model's anomaly signal with lightweight external triggers to strengthen the final score.

## Inputs
- `AnomalyDecision` from Layer 4.
- `TriggerSignals(pir_motion, thermal_presence)` from auxiliary sensors.

## Outputs
- `FusionResult(frame_number, timestamp_ms, fused_score, evidence)`.

## `.py` Files
- `sensor_fusion.py`: trigger/result classes and weighted fusion.

- `__init__.py`: public exports.

## Recommended Flow
1. Receive anomaly decision and triggers.

2. Calculate normalized `trigger_score`.

3. Combine with weights (`model_weight`, `trigger_weight`).

4. Deliver `FusionResult` to Layer 6.

## Exit Criteria (DoD)
- Reproducible and typed merge.

- Structured evidence (`dict[str, float]`) for traceability.

- Direct integration with `StateMachine`.