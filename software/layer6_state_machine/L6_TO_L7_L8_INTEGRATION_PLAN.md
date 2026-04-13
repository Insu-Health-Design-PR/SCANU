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




-------------------


cd ~/Desktop/SCANU-dev_adrian
source .venv/bin/activate

PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/full_config.cfg \
  run --mode live --mmwave on --presence mock --thermal off --max-frames 50



-----------------------------------------]]]

insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ 
PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/full_config.cfg \
  run --mode live --mmwave on --presence mock --thermal off --max-frames 50
{
  "event": {
    "previous_state": "IDLE",
    "current_state": "IDLE",
    "reason": "activity_low",
    "frame_number": 1,
    "timestamp_ms": 1775759639252.7954,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.25833333333333336,
      "confidence": 0.9375,
      "trigger_score": 0.4166666666666667,
      "anomaly_score": 0.25833333333333336
    }
  },
  "snapshot": {
    "state": "IDLE",
    "dwell_ms": 1133.74072265625,
    "fused_score": 0.25833333333333336,
    "confidence": 0.9375,
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
    "frame_number": 2,
    "timestamp_ms": 1775759639481.969,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.3666666666666667,
      "confidence": 0.9,
      "trigger_score": 0.55,
      "anomaly_score": 0.3666666666666667
    }
  },
  "snapshot": {
    "state": "TRIGGERED",
    "dwell_ms": 0.0,
    "fused_score": 0.3666666666666667,
    "confidence": 0.9,
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
    "frame_number": 3,
    "timestamp_ms": 1775759639684.4146,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.3666666666666667,
      "confidence": 0.9,
      "trigger_score": 0.55,
      "anomaly_score": 0.3666666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 0.0,
    "fused_score": 0.3666666666666667,
    "confidence": 0.9,
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
    "frame_number": 4,
    "timestamp_ms": 1775759639886.7913,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.6433333333333333,
      "confidence": 1.0,
      "trigger_score": 0.85,
      "anomaly_score": 0.6433333333333333
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 202.596923828125,
    "fused_score": 0.6433333333333333,
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
    "timestamp_ms": 1775759640089.4932,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.5183333333333333,
      "confidence": 0.9375,
      "trigger_score": 0.85,
      "anomaly_score": 0.5183333333333333
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 405.34375,
    "fused_score": 0.5183333333333333,
    "confidence": 0.9375,
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
    "frame_number": 6,
    "timestamp_ms": 1775759640292.3665,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.3416666666666667,
      "confidence": 1.0,
      "trigger_score": 0.5833333333333334,
      "anomaly_score": 0.3416666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 608.641357421875,
    "fused_score": 0.3416666666666667,
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
    "current_state": "IDLE",
    "reason": "activity_low",
    "frame_number": 7,
    "timestamp_ms": 1775759640495.4805,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.21666666666666667,
      "confidence": 0.9,
      "trigger_score": 0.3333333333333333,
      "anomaly_score": 0.21666666666666667
    }
  },
  "snapshot": {
    "state": "IDLE",
    "dwell_ms": 0.0,
    "fused_score": 0.21666666666666667,
    "confidence": 0.9,
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
    "frame_number": 8,
    "timestamp_ms": 1775759640697.6562,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.4083333333333334,
      "confidence": 0.9375,
      "trigger_score": 0.55,
      "anomaly_score": 0.4083333333333334
    }
  },
  "snapshot": {
    "state": "IDLE",
    "dwell_ms": 201.96142578125,
    "fused_score": 0.4083333333333334,
    "confidence": 0.9375,
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
    "frame_number": 9,
    "timestamp_ms": 1775759640899.5012,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.45,
      "confidence": 0.975,
      "trigger_score": 0.55,
      "anomaly_score": 0.45
    }
  },
  "snapshot": {
    "state": "TRIGGERED",
    "dwell_ms": 0.0,
    "fused_score": 0.45,
    "confidence": 0.975,
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
    "frame_number": 10,
    "timestamp_ms": 1775759641101.82,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.6016666666666667,
      "confidence": 1.0,
      "trigger_score": 0.85,
      "anomaly_score": 0.6016666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 0.0,
    "fused_score": 0.6016666666666667,
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
    "frame_number": 11,
    "timestamp_ms": 1775759641303.735,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.6016666666666667,
      "confidence": 1.0,
      "trigger_score": 0.85,
      "anomaly_score": 0.6016666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 201.809814453125,
    "fused_score": 0.6016666666666667,
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
    "frame_number": 12,
    "timestamp_ms": 1775759641505.371,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.3416666666666667,
      "confidence": 1.0,
      "trigger_score": 0.5833333333333334,
      "anomaly_score": 0.3416666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 403.455078125,
    "fused_score": 0.3416666666666667,
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
    "frame_number": 13,
    "timestamp_ms": 1775759641707.1084,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.3416666666666667,
      "confidence": 1.0,
      "trigger_score": 0.5833333333333334,
      "anomaly_score": 0.3416666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 605.122314453125,
    "fused_score": 0.3416666666666667,
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
    "frame_number": 14,
    "timestamp_ms": 1775759641908.7441,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.49166666666666675,
      "confidence": 1.0,
      "trigger_score": 0.5833333333333334,
      "anomaly_score": 0.49166666666666675
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 806.792724609375,
    "fused_score": 0.49166666666666675,
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
    "frame_number": 15,
    "timestamp_ms": 1775759642110.2803,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.3666666666666667,
      "confidence": 0.9,
      "trigger_score": 0.55,
      "anomaly_score": 0.3666666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 1008.25244140625,
    "fused_score": 0.3666666666666667,
    "confidence": 0.9,
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
    "frame_number": 16,
    "timestamp_ms": 1775759642311.759,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.5183333333333333,
      "confidence": 0.9375,
      "trigger_score": 0.85,
      "anomaly_score": 0.5183333333333333
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 1209.713623046875,
    "fused_score": 0.5183333333333333,
    "confidence": 0.9375,
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
    "frame_number": 17,
    "timestamp_ms": 1775759642513.2947,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.4766666666666667,
      "confidence": 0.9,
      "trigger_score": 0.85,
      "anomaly_score": 0.4766666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 1411.694580078125,
    "fused_score": 0.4766666666666667,
    "confidence": 0.9,
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
    "frame_number": 18,
    "timestamp_ms": 1775759642715.6826,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.25833333333333336,
      "confidence": 0.9375,
      "trigger_score": 0.4166666666666667,
      "anomaly_score": 0.25833333333333336
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 1613.928466796875,
    "fused_score": 0.25833333333333336,
    "confidence": 0.9375,
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
    "frame_number": 19,
    "timestamp_ms": 1775759642917.8247,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.25833333333333336,
      "confidence": 0.9375,
      "trigger_score": 0.4166666666666667,
      "anomaly_score": 0.25833333333333336
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 1816.071533203125,
    "fused_score": 0.25833333333333336,
    "confidence": 0.9375,
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
    "frame_number": 20,
    "timestamp_ms": 1775759643119.9146,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.45,
      "confidence": 0.975,
      "trigger_score": 0.55,
      "anomaly_score": 0.45
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 2018.122802734375,
    "fused_score": 0.45,
    "confidence": 0.975,
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
    "frame_number": 21,
    "timestamp_ms": 1775759643322.0042,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.4083333333333334,
      "confidence": 0.9375,
      "trigger_score": 0.55,
      "anomaly_score": 0.4083333333333334
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 2220.172607421875,
    "fused_score": 0.4083333333333334,
    "confidence": 0.9375,
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
    "frame_number": 22,
    "timestamp_ms": 1775759643524.0115,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.56,
      "confidence": 0.975,
      "trigger_score": 0.85,
      "anomaly_score": 0.56
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 2422.243896484375,
    "fused_score": 0.56,
    "confidence": 0.975,
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
    "frame_number": 23,
    "timestamp_ms": 1775759643726.1838,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.6016666666666667,
      "confidence": 1.0,
      "trigger_score": 0.85,
      "anomaly_score": 0.6016666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 2624.382080078125,
    "fused_score": 0.6016666666666667,
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
    "frame_number": 24,
    "timestamp_ms": 1775759643928.5125,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.3833333333333333,
      "confidence": 1.0,
      "trigger_score": 0.6666666666666666,
      "anomaly_score": 0.3833333333333333
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 2826.951904296875,
    "fused_score": 0.3833333333333333,
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
    "frame_number": 25,
    "timestamp_ms": 1775759644130.8376,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.30000000000000004,
      "confidence": 0.975,
      "trigger_score": 0.5,
      "anomaly_score": 0.30000000000000004
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 3029.2919921875,
    "fused_score": 0.30000000000000004,
    "confidence": 0.975,
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
    "frame_number": 26,
    "timestamp_ms": 1775759644333.2568,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.5333333333333333,
      "confidence": 1.0,
      "trigger_score": 0.6666666666666666,
      "anomaly_score": 0.5333333333333333
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 3231.562744140625,
    "fused_score": 0.5333333333333333,
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
    "frame_number": 27,
    "timestamp_ms": 1775759644535.538,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.5333333333333333,
      "confidence": 1.0,
      "trigger_score": 0.6666666666666666,
      "anomaly_score": 0.5333333333333333
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 3433.925537109375,
    "fused_score": 0.5333333333333333,
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
    "frame_number": 28,
    "timestamp_ms": 1775759644737.9102,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.56,
      "confidence": 0.975,
      "trigger_score": 0.85,
      "anomaly_score": 0.56
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 3636.2705078125,
    "fused_score": 0.56,
    "confidence": 0.975,
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
    "frame_number": 29,
    "timestamp_ms": 1775759644940.2297,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.56,
      "confidence": 0.975,
      "trigger_score": 0.85,
      "anomaly_score": 0.56
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 3838.465087890625,
    "fused_score": 0.56,
    "confidence": 0.975,
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
    "frame_number": 30,
    "timestamp_ms": 1775759645142.31,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.30000000000000004,
      "confidence": 0.975,
      "trigger_score": 0.5,
      "anomaly_score": 0.30000000000000004
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 4040.586669921875,
    "fused_score": 0.30000000000000004,
    "confidence": 0.975,
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
    "current_state": "IDLE",
    "reason": "activity_low",
    "frame_number": 31,
    "timestamp_ms": 1775759645344.5237,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.21666666666666667,
      "confidence": 0.9,
      "trigger_score": 0.3333333333333333,
      "anomaly_score": 0.21666666666666667
    }
  },
  "snapshot": {
    "state": "IDLE",
    "dwell_ms": 0.0,
    "fused_score": 0.21666666666666667,
    "confidence": 0.9,
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
    "frame_number": 32,
    "timestamp_ms": 1775759645546.5786,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.45,
      "confidence": 0.975,
      "trigger_score": 0.55,
      "anomaly_score": 0.45
    }
  },
  "snapshot": {
    "state": "IDLE",
    "dwell_ms": 202.045654296875,
    "fused_score": 0.45,
    "confidence": 0.975,
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
    "frame_number": 33,
    "timestamp_ms": 1775759645748.586,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.6583333333333333,
      "confidence": 1.0,
      "trigger_score": 0.9166666666666666,
      "anomaly_score": 0.6583333333333333
    }
  },
  "snapshot": {
    "state": "TRIGGERED",
    "dwell_ms": 0.0,
    "fused_score": 0.6583333333333333,
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
    "frame_number": 34,
    "timestamp_ms": 1775759645950.6619,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.6016666666666667,
      "confidence": 1.0,
      "trigger_score": 0.85,
      "anomaly_score": 0.6016666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 0.0,
    "fused_score": 0.6016666666666667,
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
    "frame_number": 35,
    "timestamp_ms": 1775759646152.6843,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.7266666666666667,
      "confidence": 1.0,
      "trigger_score": 0.85,
      "anomaly_score": 0.7266666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 201.923095703125,
    "fused_score": 0.7266666666666667,
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
    "frame_number": 36,
    "timestamp_ms": 1775759646354.5566,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.3416666666666667,
      "confidence": 1.0,
      "trigger_score": 0.5833333333333334,
      "anomaly_score": 0.3416666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 403.71337890625,
    "fused_score": 0.3416666666666667,
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
    "frame_number": 37,
    "timestamp_ms": 1775759646556.3088,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.42500000000000004,
      "confidence": 1.0,
      "trigger_score": 0.75,
      "anomaly_score": 0.42500000000000004
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 605.65283203125,
    "fused_score": 0.42500000000000004,
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
    "frame_number": 38,
    "timestamp_ms": 1775759646758.438,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.3666666666666667,
      "confidence": 0.9,
      "trigger_score": 0.55,
      "anomaly_score": 0.3666666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 807.806396484375,
    "fused_score": 0.3666666666666667,
    "confidence": 0.9,
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
    "frame_number": 39,
    "timestamp_ms": 1775759646960.7578,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.45,
      "confidence": 0.975,
      "trigger_score": 0.55,
      "anomaly_score": 0.45
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 1010.251708984375,
    "fused_score": 0.45,
    "confidence": 0.975,
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
    "frame_number": 40,
    "timestamp_ms": 1775759647163.1726,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.56,
      "confidence": 0.975,
      "trigger_score": 0.85,
      "anomaly_score": 0.56
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 1212.514404296875,
    "fused_score": 0.56,
    "confidence": 0.975,
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
    "frame_number": 41,
    "timestamp_ms": 1775759647365.349,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.56,
      "confidence": 0.975,
      "trigger_score": 0.85,
      "anomaly_score": 0.56
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 1414.686279296875,
    "fused_score": 0.56,
    "confidence": 0.975,
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
    "frame_number": 42,
    "timestamp_ms": 1775759647567.603,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.30000000000000004,
      "confidence": 0.975,
      "trigger_score": 0.5,
      "anomaly_score": 0.30000000000000004
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 1617.128662109375,
    "fused_score": 0.30000000000000004,
    "confidence": 0.975,
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
    "frame_number": 43,
    "timestamp_ms": 1775759647770.0408,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.3416666666666667,
      "confidence": 1.0,
      "trigger_score": 0.5833333333333334,
      "anomaly_score": 0.3416666666666667
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 1819.483154296875,
    "fused_score": 0.3416666666666667,
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
    "frame_number": 44,
    "timestamp_ms": 1775759647972.4016,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.4083333333333334,
      "confidence": 0.9375,
      "trigger_score": 0.55,
      "anomaly_score": 0.4083333333333334
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 2021.811279296875,
    "fused_score": 0.4083333333333334,
    "confidence": 0.9375,
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
    "frame_number": 45,
    "timestamp_ms": 1775759648175.0063,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.5333333333333333,
      "confidence": 1.0,
      "trigger_score": 0.6666666666666666,
      "anomaly_score": 0.5333333333333333
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 2224.4052734375,
    "fused_score": 0.5333333333333333,
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
    "frame_number": 46,
    "timestamp_ms": 1775759648377.2148,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.56,
      "confidence": 0.975,
      "trigger_score": 0.85,
      "anomaly_score": 0.56
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 2426.760009765625,
    "fused_score": 0.56,
    "confidence": 0.975,
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
    "frame_number": 47,
    "timestamp_ms": 1775759648579.7515,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.56,
      "confidence": 0.975,
      "trigger_score": 0.85,
      "anomaly_score": 0.56
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 2629.324951171875,
    "fused_score": 0.56,
    "confidence": 0.975,
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
    "frame_number": 48,
    "timestamp_ms": 1775759648782.2888,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.25833333333333336,
      "confidence": 0.9375,
      "trigger_score": 0.4166666666666667,
      "anomaly_score": 0.25833333333333336
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 2831.741455078125,
    "fused_score": 0.25833333333333336,
    "confidence": 0.9375,
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
    "frame_number": 49,
    "timestamp_ms": 1775759648984.6306,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.30000000000000004,
      "confidence": 0.975,
      "trigger_score": 0.5,
      "anomaly_score": 0.30000000000000004
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 3034.056640625,
    "fused_score": 0.30000000000000004,
    "confidence": 0.975,
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
    "frame_number": 50,
    "timestamp_ms": 1775759649187.02,
    "radar_id": "radar_main",
    "scores": {
      "fused_score": 0.45,
      "confidence": 0.975,
      "trigger_score": 0.55,
      "anomaly_score": 0.45
    }
  },
  "snapshot": {
    "state": "SCANNING",
    "dwell_ms": 3236.543701171875,
    "fused_score": 0.45,
    "confidence": 0.975,
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


