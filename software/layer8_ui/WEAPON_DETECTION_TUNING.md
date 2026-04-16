# Weapon Detection Tuning Log

Use this sheet to tune multi-person weapon detection behavior, reduce phone false positives, and keep stable runtime performance.

## Baseline Configuration

| Parameter | Value | Notes |
|---|---:|---|
| `person_detection_conf` | 0.30 | Person detector confidence |
| `weapon_gun_conf` | 0.35 | Weapon YOLO confidence |
| `weapon_gun_threshold` | 0.60 | Final weapon decision threshold |
| `weapon_gun_min_box_px` | 80 | Minimum weapon box size |
| `weapon_min_box_px` | 32 | Global minimum weapon ROI size |
| `weapon_person_iou_min` | 0.15 | Minimum overlap with assigned person |
| `weapon_person_center_max_norm` | 0.35 | Max normalized center distance |
| `multi_person_exclusive_assignment` | true | 1 weapon box assigned to 1 person only |
| `frames_to_confirm_weapon` | 3 of 5 | Temporal confirmation |
| `frames_to_clear_weapon` | 4 of 6 | Temporal clear logic |

## Scenario Configurations

| Scenario | Goal | `weapon_gun_conf` | `weapon_gun_threshold` | `weapon_gun_min_box_px` | Assignment Rule | Temporal Rule |
|---|---|---:|---:|---:|---|---|
| 1 person armed (close) | High precision | 0.35 | 0.60 | 80 | `IoU >= 0.15` + center dist <= 0.35 | 3/5 confirm |
| 2 persons, only 1 armed | Prevent both marked armed | 0.35 | 0.60 | 80 | Exclusive assignment (nearest+IoU) | 3/5 confirm |
| 2 persons, no weapon (phones) | Reduce phone false positives | 0.40 | 0.65 | 96 | `IoU >= 0.20` | 4/6 confirm |
| Partial occlusion | Keep recall under occlusion | 0.30 | 0.50 | 64 | `IoU >= 0.10` + center dist <= 0.40 | 3/5 confirm |
| Medium/long distance | Detect small true weapons | 0.25 | 0.50 | 48 | `IoU >= 0.10` | 3/5 confirm |

## Test Execution Order

1. Run baseline and record metrics.
2. Run "2 persons, only 1 armed" and verify assignment behavior.
3. Run "no weapon, phones visible" and tune false positives.
4. Run occlusion and long-distance scenarios.
5. Select final compromise profile (precision vs recall).

## Metrics to Record Per Run

- `TP` (true weapon detections)
- `FN` (missed weapons)
- `FP_phone` (phone false positives)
- `FP_multi_person` (wrongly marks multiple people armed)
- `latency_ms`
- `fps`
- `time_to_first_detection_ms`

## Run Log (Fill In)

| Date | Scenario | Profile Name | TP | FN | FP_phone | FP_multi_person | Latency (ms) | FPS | Notes |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
|  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |

## Notes (English)

### General Notes
- 
- 
- 

### What Improved
- 
- 

### What Regressed
- 
- 

### Next Experiment
- Hypothesis:
- Parameters to change:
- Expected impact:

## Final Selected Profile

- Profile name:
- Reason selected:
- Final parameter set:
  - `person_detection_conf = `
  - `weapon_gun_conf = `
  - `weapon_gun_threshold = `
  - `weapon_gun_min_box_px = `
  - `weapon_person_iou_min = `
  - `multi_person_exclusive_assignment = `
  - `frames_to_confirm_weapon = `
  - `frames_to_clear_weapon = `
