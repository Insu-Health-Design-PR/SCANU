# Layer 5: Multi-Sensor Fusion

## Responsibilities
- Accept raw sensor signals from Layer 1 (mmWave points/heatmaps), Layer 2
  (weapon tracker confidence, micro-Doppler bandwidth), and Layer 4 (thermal
  gun-detection metadata).
- Compute a weighted `FusionInputContract` that prioritises weapon-specific
  signatures (micro-Doppler, RCS proxy, azimuth-static peak) alongside
  presence, motion, and thermal scores.
- Produce a single `fused_score` and `anomaly_score` for the Layer 6 state
  machine.

## Inputs (via `FusionInputContract`)

| Field | Source | Weight |
|-------|--------|--------|
| `mmwave_score` | L1 point-cloud density | 0.45 × sensor_factor |
| `presence_score` | L1 Infineon LTR11 | 0.20 × sensor_factor |
| `motion_score` | L1 Infineon LTR11 | 0.20 × sensor_factor |
| `thermal_score` | L1 thermal camera delta | 0.15 × sensor_factor |
| `weapon_score` | L2 WeaponTracker + micro-Doppler | 0.50 weapon_factor |
| `gun_detected_boost` | L4 thermal YOLO gun detection | +0.45 min |

## Output

`FusionInputContract` consumed by Layer 6 `StateMachine.update()`:
- `fused_score: float` — global anomaly score (0–1)
- `confidence: float` — meta-confidence in the score
- `trigger_score: float` — max of all sensor scores (used for TRIGGERED state)
- `anomaly_score: float` — weighted sensor combination (used for ANOMALY_DETECTED)
- `evidence: dict[str, float]` — 16 diagnostic fields

## Key classes

| Class | File | Purpose |
|-------|------|---------|
| `FusionInputContract` | `models.py` | Data contract between L5 and L6 |
| `L1L2FusionAdapter` | `fusion_adapter.py` | Weighted fusion engine |

## Usage

```python
from layer5_fusion import L1L2FusionAdapter

adapter = L1L2FusionAdapter(weapon_weight=0.50)
contract = adapter.adapt(raw_inputs, radar_id="radar_main")
# contract.fused_score, contract.anomaly_score, ...
```
