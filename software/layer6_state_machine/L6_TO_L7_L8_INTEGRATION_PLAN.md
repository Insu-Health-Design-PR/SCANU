# L6 -> L7 -> L8 Integration Plan (Temporary)

## Summary
This plan defines the post-validation integration path from Layer 6 (state/control) into Layer 7 (alerts/logging) and Layer 8 (backend/UI stream), using the current `Layer6Orchestrator` outputs (`StateEvent`, `StateSnapshot`, optional `ActionRequest`).

Success means:
- Layer 7 receives and transforms Layer 6 events into normalized alerts.
- Layer 8 exposes current status + live stream + recent alert history.
- End-to-end scenarios (normal, anomaly, fault, recovery) are visible in backend outputs and UI stream.

## Implementation Changes

### 1) Layer 7 alert pipeline
- Implement an `AlertManager` that maps `StateEvent.current_state` into alert levels:
  - `IDLE` -> `INFO`
  - `TRIGGERED` / `SCANNING` -> `WARNING`
  - `ANOMALY_DETECTED` -> `ALERT`
  - `FAULT` -> `FAULT`
- Emit a typed `AlertPayload` with:
  - `event_id`, `timestamp_utc`, `level`, `state`, `message`, `radar_id`, `scores`, `metadata`
- Add an `EventLogger` (append-only) for audit + replay and expose query helpers:
  - `append(payload)`
  - `recent(limit)`
  - `by_level(level, limit)`

### 2) Layer 8 backend stream integration
- Add backend contracts for:
  - latest `StateSnapshot`
  - latest `AlertPayload`
  - recent alerts list
- Add API endpoints:
  - `GET /api/status`
  - `GET /api/alerts/recent`
  - `GET /api/health`
- Add WebSocket event encoding with event types:
  - `status_update`
  - `alert_event`
  - `sensor_fault`
  - `heartbeat`
- Ensure Layer 6 tick loop pushes state and alerts to backend publisher.

### 3) Layer 6 integration hooks
- Keep Layer 6 APIs unchanged.
- Add a lightweight integration adapter that forwards:
  - `StateEvent` -> Layer 7 `AlertManager`
  - `StateSnapshot` -> Layer 8 status store
- Preserve `ActionRequest` flow for operational actions (e.g., soft reset recommendation on fault).

### 4) Operational wiring
- Extend current runtime/runner flow so one command can:
  - run Layer 6 loop
  - generate Layer 7 alerts
  - publish Layer 8 status/stream
- Keep destructive control actions manual-only (`kill`, `usb-reset`), unchanged from current policy.

## Public Interfaces (New/Updated)
- `AlertManager.build(state_event) -> AlertPayload`
- `EventLogger.append(payload) -> None`
- `EventLogger.recent(limit=50) -> list[AlertPayload]`
- `BackendStateStore.update_status(snapshot) -> None`
- `BackendStateStore.publish_alert(payload) -> None`
- `WebSocketStream.encode_status(snapshot) -> dict`
- `WebSocketStream.encode_alert(payload) -> dict`

## Test Plan
1. Unit tests:
- state-to-alert mapping for all `SystemState` values
- alert payload schema completeness
- logger append/recent ordering
- websocket encoding for status/alert events

2. Integration tests:
- L6 tick -> L7 payload generated
- L6 tick -> L8 status updated
- anomaly scenario emits `ALERT`
- fault scenario emits `FAULT` and recovery path updates status correctly

3. End-to-end smoke:
- run in simulate mode and verify:
  - `/api/status` changes over time
  - `/api/alerts/recent` receives expected records
  - websocket stream emits `status_update` and `alert_event`

## Assumptions and Defaults
- Keep current Layer 6 contracts unchanged to avoid rework.
- Use existing provisional L1/L2 fusion input until Layer 5 real output is connected.
- Initial persistence can be in-memory (or local JSON/SQLite) as long as retrieval APIs are stable.
- This document is temporary and should be replaced by implementation notes after validation passes.



















----------------------


insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ cd ~/SCANU-dev_adrian
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r software/layer1_radar/requirements.txt
bash: cd: /home/insu/SCANU-dev_adrian: No such file or directory
Requirement already satisfied: pip in ./.venv/lib/python3.10/site-packages (22.0.2)
Collecting pip
  Using cached pip-26.0.1-py3-none-any.whl (1.8 MB)
Installing collected packages: pip
  Attempting uninstall: pip
    Found existing installation: pip 22.0.2
    Uninstalling pip-22.0.2:
      Successfully uninstalled pip-22.0.2
Successfully installed pip-26.0.1
Collecting pyserial>=3.5 (from -r software/layer1_radar/requirements.txt (line 5))
  Using cached pyserial-3.5-py2.py3-none-any.whl.metadata (1.6 kB)
Collecting numpy>=1.21.0 (from -r software/layer1_radar/requirements.txt (line 8))
  Using cached numpy-2.2.6-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (63 kB)
Using cached pyserial-3.5-py2.py3-none-any.whl (90 kB)
Using cached numpy-2.2.6-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.3 MB)
Installing collected packages: pyserial, numpy
Successfully installed numpy-2.2.6 pyserial-3.5
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main run --mode simulate --max-frames 5
{
  "event": {
    "previous_state": "IDLE",
    "current_state": "IDLE",
    "reason": "activity_low",
    "frame_number": 1,
    "timestamp_ms": 1775752834783.9517,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.08000000000000002,
      "confidence": 0.9500000000000001,
      "trigger_score": 0.2,
      "anomaly_score": 0.08000000000000002
    }
  },
  "snapshot": {
    "state": "IDLE",
    "dwell_ms": 0.301025390625,
    "fused_score": 0.08000000000000002,
    "confidence": 0.9500000000000001,
    "health": {
      "has_fault": false,
      "fault_code": null,
      "sensor_online_count": 1
    },
    "active_radars": [
      "radar_main"
    ]
  },
  "action_request": null
}
{
  "event": {
    "previous_state": "IDLE",
    "current_state": "IDLE",
    "reason": "activity_low",
    "frame_number": 2,
    "timestamp_ms": 1775752834985.0344,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.2916666666666667,
      "confidence": 0.9875,
      "trigger_score": 0.6,
      "anomaly_score": 0.2916666666666667
    }
  },
  "snapshot": {
    "state": "IDLE",
    "dwell_ms": 201.461181640625,
    "fused_score": 0.2916666666666667,
    "confidence": 0.9875,
    "health": {
      "has_fault": false,
      "fault_code": null,
      "sensor_online_count": 1
    },
    "active_radars": [
      "radar_main"
    ]
  },
  "action_request": null
}
{
  "event": {
    "previous_state": "IDLE",
    "current_state": "TRIGGERED",
    "reason": "trigger_detected",
    "frame_number": 3,
    "timestamp_ms": 1775752835186.6484,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.33333333333333337,
      "confidence": 1.0,
      "trigger_score": 0.6,
      "anomaly_score": 0.33333333333333337
    }
  },
  "snapshot": {
    "state": "TRIGGERED",
    "dwell_ms": 0.0,
    "fused_score": 0.33333333333333337,
    "confidence": 1.0,
    "health": {
      "has_fault": false,
      "fault_code": null,
      "sensor_online_count": 1
    },
    "active_radars": [
      "radar_main"
    ]
  },
  "action_request": null
}
{
  "event": {
    "previous_state": "TRIGGERED",
    "current_state": "SCANNING",
    "reason": "scan_window_active",
    "frame_number": 4,
    "timestamp_ms": 1775752835388.2646,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.28500000000000003,
      "confidence": 1.0,
      "trigger_score": 0.6,
      "anomaly_score": 0.28500000000000003
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 0.0,
    "fused_score": 0.28500000000000003,
    "confidence": 1.0,
    "health": {
      "has_fault": false,
      "fault_code": null,
      "sensor_online_count": 1
    },
    "active_radars": [
      "radar_main"
    ]
  },
  "action_request": null
}
{
  "event": {
    "previous_state": "SCANNING",
    "current_state": "SCANNING",
    "reason": "scan_window_active",
    "frame_number": 5,
    "timestamp_ms": 1775752835589.8574,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.4666666666666666,
      "confidence": 1.0,
      "trigger_score": 0.7,
      "anomaly_score": 0.4666666666666666
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 201.6123046875,
    "fused_score": 0.4666666666666666,
    "confidence": 1.0,
    "health": {
      "has_fault": false,
      "fault_code": null,
      "sensor_online_count": 1
    },
    "active_radars": [
      "radar_main"
    ]
  },
  "action_request": null
}
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main status
{
  "radar_id": "radar_main",
  "connected": true,
  "configured": false,
  "streaming": false,
  "fault_code": null,
  "last_seen_ms": 1775752870636.7358,
  "config_port": null,
  "data_port": null
}
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/full_config.cfg \
  reconfig
{
  "radar_id": "radar_main",
  "action": "apply_config",
  "success": true,
  "message": "Radar configured",
  "details": {
    "source": "software/layer1_sensor_hub/testing/configs/full_config.cfg",
    "commands_sent": 30,
    "errors": []
  }
}
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  run --mode live --mmwave on --presence mock --thermal off --max-frames 50
Command 28 'sensorStart': sensorStart
Error: You have provided partial configuration between stop and this command and partial configuration cannot be undone.Issue the full configuration and do "sensorStart" 
Error -1
mmwDemo:/>
mmwDemo:/>
Configuration had 1 errors
Traceback (most recent call last):
  File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/layer6_state_machine/run_layer6.py", line 257, in <module>
    raise SystemExit(main())
  File "/home/insu/Desktop/SCANU-dev_adrian/software/layer6_state_machine/run_layer6.py", line 223, in main
    return _run_command(orchestrator, args)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/layer6_state_machine/run_layer6.py", line 118, in _run_command
    hub, serial_mgr = _build_live_hub(args)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/layer6_state_machine/run_layer6.py", line 74, in _build_live_hub
    raise RuntimeError(f"mmWave configure failed: {result.errors[:3]}")
RuntimeError: mmWave configure failed: ['Command 28 \'sensorStart\': sensorStart\r\nError: You have provided partial configuration between stop and this command and partial configuration cannot be undone.Issue the full configuration and do "sensorStart" \n\rError -1\n\rmmwDemo:/>\nmmwDemo:/>']
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  run --mode live --mmwave on --presence mock --thermal off --max-frames 0
Command 28 'sensorStart': sensorStart
Error: You have provided partial configuration between stop and this command and partial configuration cannot be undone.Issue the full configuration and do "sensorStart" 
Error -1
mmwDemo:/>
mmwDemo:/>
Configuration had 1 errors
Traceback (most recent call last):
  File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/layer6_state_machine/run_layer6.py", line 257, in <module>
    raise SystemExit(main())
  File "/home/insu/Desktop/SCANU-dev_adrian/software/layer6_state_machine/run_layer6.py", line 223, in main
    return _run_command(orchestrator, args)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/layer6_state_machine/run_layer6.py", line 118, in _run_command
    hub, serial_mgr = _build_live_hub(args)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/layer6_state_machine/run_layer6.py", line 74, in _build_live_hub
    raise RuntimeError(f"mmWave configure failed: {result.errors[:3]}")
RuntimeError: mmWave configure failed: ['Command 28 \'sensorStart\': sensorStart\r\nError: You have provided partial configuration between stop and this command and partial configuration cannot be undone.Issue the full configuration and do "sensorStart" \n\rError -1\n\rmmwDemo:/>\nmmwDemo:/>']
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  reset
[info] sensorStop rsp: sensorStop
Ignored: Sensor is already stopped
Done
mmwDemo:/>
mmwDemo:/>
[ok] soft reset: sent sensorStop
[ok] soft reset: DATA flush 0 bytes
{
  "radar_id": "radar_main",
  "action": "reset_soft",
  "success": true,
  "message": "Soft reset executed",
  "details": {
    "config_port": "/dev/ttyUSB0",
    "data_port": "/dev/ttyUSB1"
  }
}
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  kill --force --confirm-manual
[warn] fuser failed for /dev/ttyUSB0: /dev/ttyUSB0:
[warn] fuser failed for /dev/ttyUSB1: /dev/ttyUSB1:
{
  "radar_id": "radar_main",
  "action": "kill_holders",
  "success": true,
  "message": "Holder processes terminated",
  "details": {
    "pid_count": 0,
    "force": true
  }
}
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  usb-reset --confirm-manual
[info] resetting USB device at /sys/devices/platform/bus@0/3610000.usb/usb1/1-2/1-2.2/1-2.2:1.0
[sudo] password for insu: 
[ok] USB reset complete
[info] resetting USB device at /sys/devices/platform/bus@0/3610000.usb/usb1/1-2/1-2.2/1-2.2:1.1
[ok] USB reset complete
{
  "radar_id": "radar_main",
  "action": "usb_reset",
  "success": true,
  "message": "USB reset requested",
  "details": {
    "ports": [
      "/dev/ttyUSB0",
      "/dev/ttyUSB1"
    ]
  }
}
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --aux-radar radar_aux_1:/dev/ttyUSB2:/dev/ttyUSB3:software/layer1_sensor_hub/testing/configs/full_config.cfg \
  status
{
  "radar_id": "radar_main",
  "connected": true,
  "configured": false,
  "streaming": false,
  "fault_code": null,
  "last_seen_ms": 1775753008968.618,
  "config_port": "/dev/ttyUSB0",
  "data_port": "/dev/ttyUSB1"
}
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ 

