# Layer 4: AI Inference Engine

## Objective
Convert feature vectors from upstream processing into a calibrated anomaly score and a decision contract that downstream layers can consume deterministically.

This layer supports two execution tiers:
- MVP: deterministic lightweight scorer in Python/NumPy
- Production: ONNX model with TensorRT acceleration on Jetson Orin Nano

## Runtime Target
- Development: PC (x86_64) with Python 3.10+
- Edge deployment: Jetson Orin Nano with JetPack 6.x

## Inputs
Primary input contract from Layer 3:
- FeatureBatch(frame_number, timestamp_ms, vector, metadata)

Compatible fallback input:
- HeatmapFeatures from Layer 2 when Layer 3 vectorization is bypassed

Optional context:
- Sensor health and quality flags
- Calibration phase indicator

## Outputs
- InferenceResult(frame_number, timestamp_ms, raw_score, confidence, model_version, latency_ms)
- AnomalyDecision(frame_number, timestamp_ms, anomaly_score, confidence, threshold, is_anomaly, reason)

## Responsibilities
- Validate feature shape and dtype
- Normalize model input
- Run runtime backend (deterministic, onnxruntime, tensorrt)
- Calibrate score to [0, 1]
- Produce confidence and thresholded decision
- Emit model version and latency telemetry

## Recommended Python Files
- inference_engine.py: runtime abstraction and infer()
- anomaly_scorer.py: threshold policy, confidence gate, hysteresis
- model_registry.py: model loading, checksums, version metadata
- __init__.py: exports

## Interface Contracts
InferenceEngine:
- infer(feature_batch) -> InferenceResult
- Deterministic output for identical input/model
- Explicit typed errors on shape/version mismatch

AnomalyScorer:
- evaluate(inference_result) -> AnomalyDecision
- Supports static threshold, confidence floor, optional hysteresis

## Performance Targets
- Layer latency target: under 20 ms per frame on Jetson for MVP model
- Model size target: under 10 MB
- Cold-start model load target: under 2 s

## Error Handling
- On model runtime failure:
- fallback to deterministic scorer
- set reason to model_runtime_fallback
- On invalid input:
- reject frame with structured error
- keep pipeline loop alive

## Observability
Per-frame metrics and logs:
- model_backend and model_version
- inference_latency_ms
- raw_score, confidence, threshold, decision

## Recommended Flow
1. Receive FeatureBatch.
2. Validate shape and normalize features.
3. Execute selected runtime backend.
4. Compute calibrated score and confidence.
5. Apply threshold policy to produce AnomalyDecision.
6. Forward to Layer 5.

## Definition of Done (DoD)
- Typed contracts implemented and documented
- Unit tests for deterministic output and threshold behavior
- Backend abstraction includes deterministic and ONNX path
- Jetson-ready TensorRT configuration path
- Integration test from Layer 3 input to Layer 5 handoff
