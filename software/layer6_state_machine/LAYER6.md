# Layer 6: Alert State Machine

## Objective
Orchestrate overall system behavior using explicit states and deterministic transitions based on fused score, trigger continuity, and system faults.

## States
- IDLE
- TRIGGERED
- SCANNING
- ANOMALY_DETECTED
- FAULT

## Inputs
- FusionResult from Layer 5
- has_fault flag from monitoring
- Optional operational signals:
- calibration_in_progress
- sensor_online_count

## Outputs
- StateEvent(previous_state, current_state, reason, frame_number, timestamp_ms)
- StateSnapshot(current_state, dwell_ms, score, fault_code)

## Responsibilities
- Apply transition rules in deterministic order
- Prioritize FAULT transitions above all others
- Enforce dwell and hysteresis windows to avoid oscillation
- Emit structured events for Layer 7 alerting and Layer 8 UI

## Recommended Python Files
- state_machine.py: state enum, transitions, update()
- transition_policy.py: thresholds, timers, hysteresis rules
- __init__.py: exports

## Transition Priority
1. FAULT path has highest priority
2. Alert path from sustained high fused score
3. Trigger and scanning path from moderate activity
4. Return to IDLE when activity decays

## Suggested Transition Rules
- IDLE -> TRIGGERED when trigger_score exceeds trigger_threshold
- TRIGGERED -> SCANNING when trigger remains active for min_trigger_frames
- SCANNING -> ANOMALY_DETECTED when fused_score exceeds anomaly_threshold for min_anomaly_frames
- Any state -> FAULT when has_fault is true
- FAULT -> IDLE only after explicit clear and health recovery

## Timing Guidance
- Trigger dwell: 200 to 500 ms
- Scanning window: 1 to 3 s
- Alert hysteresis: separate enter and exit thresholds

## Recommended Flow
1. Receive FusionResult and system health flags.
2. Evaluate fault condition first.
3. Evaluate anomaly and trigger transitions.
4. Apply dwell and hysteresis constraints.
5. Emit StateEvent and updated snapshot.
6. Forward state event to Layer 7 and status to Layer 8.

## Observability
Per-transition logs:
- previous_state and current_state
- transition_reason
- fused_score and thresholds
- dwell_ms

## Definition of Done (DoD)
- Explicit enum-based state machine implemented
- Deterministic transition table with tests
- Hysteresis and dwell logic validated
- Clear FAULT handling and recovery path
- Integration validated with Layer 5 and Layer 7
