# Anomaly Report From Capture - Commands

Use this guide to run `anomaly_report_from_capture.py` with the current repository paths.

## 1) Go to repo root

```bash
cd /Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU
```

## 2) Run using your current 2-people captures

### Threat case (person concealed object)

```bash
python3 software/layer1_sensor_hub/testing/view/anomaly_report_from_capture.py \
  --capture-json "software/layer1_sensor_hub/testing/view/two_people_one_threat_sens_report_person_concealed_object_capture.json"
```

### No-threat case (person unarmed)

```bash
python3 software/layer1_sensor_hub/testing/view/anomaly_report_from_capture.py \
  --capture-json "software/layer1_sensor_hub/testing/view/two_people_one_threat_sens_report_person_unarmed_capture.json"
```

### Baseline case (empty room)

```bash
python3 software/layer1_sensor_hub/testing/view/anomaly_report_from_capture.py \
  --capture-json "software/layer1_sensor_hub/testing/view/two_people_one_threat_sens_report_empty_room_capture.json"
```

## 3) Save output with custom report path

```bash
python3 software/layer1_sensor_hub/testing/view/anomaly_report_from_capture.py \
  --capture-json "software/layer1_sensor_hub/testing/view/two_people_one_threat_sens_report_person_concealed_object_capture.json" \
  --output "software/layer1_sensor_hub/testing/view/two_people_one_threat_sens_report_person_concealed_object_report_from_custom.json"
```

## 4) Sensitive tuning (more likely to alert)

```bash
python3 software/layer1_sensor_hub/testing/view/anomaly_report_from_capture.py \
  --capture-json "software/layer1_sensor_hub/testing/view/two_people_one_threat_sens_report_person_concealed_object_capture.json" \
  --mmwave-risk-th 0.025 \
  --thermal-support-delta-th 0.8 \
  --min-consecutive 2
```

## 5) Compare all three quickly

```bash
python3 software/layer1_sensor_hub/testing/view/anomaly_report_from_capture.py \
  --capture-json "software/layer1_sensor_hub/testing/view/two_people_one_threat_sens_report_empty_room_capture.json"

python3 software/layer1_sensor_hub/testing/view/anomaly_report_from_capture.py \
  --capture-json "software/layer1_sensor_hub/testing/view/two_people_one_threat_sens_report_person_unarmed_capture.json"

python3 software/layer1_sensor_hub/testing/view/anomaly_report_from_capture.py \
  --capture-json "software/layer1_sensor_hub/testing/view/two_people_one_threat_sens_report_person_concealed_object_capture.json"
```

