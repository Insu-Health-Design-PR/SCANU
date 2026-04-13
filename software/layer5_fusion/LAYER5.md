# Layer 5: Sensor Fusion

## Objective
Combine **mmWave / capture JSON** signals with **Layer 4 thermal inference** (person-crop scores and discrete labels) into a single, auditable result for downstream state and alerts.

## Inputs
- Raw **capture JSON** (`frames[].mmwave`, optional `thermal` / `presence`), including `risk_score_mmwave` when present.
- **Layer 4 / weapon_ai** (`ThermalThreatDetector` + `InferenceEngine` + `AnomalyScorer` from `layer4_inference.weapon_ai.threat_engine`, same stack as `infer_thermal_objects`): per-frame labels `unarmed` | `suspicious` | `armed` (exported to fusion as `no_threat` | `suspicious` | `threat`).

## Outputs
- **Fused report JSON** with `status` (`ALERT` / `NO_ALERT`), `segments`, and `fusion_verdict.overall` in **`threat` | `suspicious` | `no_threat`** aligned with alert segments and peak-frame Layer 4 labels.

## `.py` Files
- `capture_fusion.py`: scoring, temporal rules, optional video-aligned Layer 4 pass, `fusion_verdict`.
- `anomaly_report_from_capture.py`: CLI entry (`python -m layer5_fusion.anomaly_report_from_capture` from `software/`).
- `__init__.py`: exports `main` / `build_parser` for tooling.

## Recommended Flow
1. Ingest capture JSON (+ optional thermal video path from `capture_info.video` or `--video`).
2. Sample thermal frames, run Layer 4, forward-fill scores/labels to every capture index.
3. Fuse mmWave risk with presence / thermal delta / model score; require thermal support (mean delta or Layer 4 suspicious+).
4. Emit segments, summary, and `fusion_verdict` for Layer 6.

## Exit Criteria (DoD)
- Typed inference boundary (`layer4_inference.weapon_ai.threat_engine`).
- Structured JSON with traceable thresholds and preview rows.
- **Public verdict vocabulary**: `threat` / `suspicious` / `no_threat` on the fusion output (Layer 4 still uses `armed` internally).
