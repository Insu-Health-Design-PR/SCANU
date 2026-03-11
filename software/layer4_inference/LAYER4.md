# Layer 4: AI Inference

## Objective
Apply lightweight inference and anomaly scoring to convert features into an interpretable decision.

## Inputs
- `FeatureBatch` from Layer 3.

## Outputs
- `InferenceResult(frame_number, timestamp_ms, raw_score, confidence)`.

- `AnomalyDecision(frame_number, timestamp_ms, anomaly_score, confidence, is_anomaly)`.

## `.py` Files
- `inference_engine.py`: deterministic calculation of `raw_score` and `confidence`.

- `anomaly_scorer.py`: configurable thresholding for binary decisions.

- `__init__.py`: public exports.

## Recommended Flow
1. `InferenceEngine.infer()` transforms the feature vector into a continuous score.

` ... 2. `AnomalyScorer.evaluate()` combines score and confidence.

3. `AnomalyDecision` is issued for Layer 5.

## Exit Criteria (DoD)
- Low-cost, deterministic inference.

- Configurable threshold without heavy production logic.

- Contracts ready for multisensor fusion.