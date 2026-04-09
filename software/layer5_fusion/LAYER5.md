# Layer 5: Multi-Sensor Fusion

## Objective
Fuse anomaly intelligence from Layer 4 with external sensor triggers (PIR, 60 GHz presence, optional thermal and auxiliary sensors) into one final score with traceable evidence.

## Inputs
- AnomalyDecision from Layer 4
- TriggerSignals from auxiliary sensors:
- pir_motion
- presence_60g
- thermal_presence (optional)
- sensor_health indicators (optional)

## Outputs
- FusionResult(frame_number, timestamp_ms, fused_score, confidence, is_alert_candidate, evidence)

Evidence dictionary should include normalized components, for example:
- model_score
- trigger_score
- pir_weighted
- presence_weighted
- health_penalty

## Responsibilities
- Normalize each input signal to [0, 1]
- Apply weighted scoring with configurable profiles
- Penalize low-quality or unstable sensor inputs
- Keep explainability with clear evidence fields
- Keep runtime deterministic and low latency

## Recommended Python Files
- sensor_fusion.py: contracts and fusion logic
- fusion_config.py: weight profiles (mvp, sensitive, conservative)
- __init__.py: exports

## Reference Fusion Formula
fused_score = model_weight * model_score + trigger_weight * trigger_score - health_penalty

Suggested MVP defaults:
- model_weight = 0.7
- trigger_weight = 0.3
- trigger decomposition example:
- 0.5 * pir_motion
- 0.5 * presence_60g

## Operating Modes
- normal: balanced sensitivity
- sensitive: lower threshold and higher trigger contribution
- conservative: higher threshold and stronger confidence requirement

## Guardrails
- If one sensor is missing, continue with available sensors
- If all triggers are missing, fallback to model-only fusion
- Never block the pipeline because one trigger frame is absent

## Recommended Flow
1. Receive AnomalyDecision and latest trigger snapshot.
2. Normalize and validate all inputs.
3. Compute per-source contributions.
4. Compute fused_score and confidence.
5. Build structured evidence dictionary.
6. Forward FusionResult to Layer 6.

## Observability
Track per-frame telemetry:
- fused_score
- model_score
- trigger_score
- selected mode
- missing_sources

## Definition of Done (DoD)
- Typed fusion contracts implemented
- Reproducible weighted scoring behavior
- Unit tests for missing-sensor and mode scenarios
- Evidence map available for audit and demos
- Integration handoff to Layer 6 validated
