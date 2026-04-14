# Layer 6: State Machine

## Objective
To orchestrate the overall system behavior using explicit states based on fused scores and faults.

## Inputs
- `FusionResult` from Layer 5.
- `has_fault` flag from internal monitoring.

## Outputs
- `StateEvent(previous_state, current_state, reason)`.

## .py Files
- `state_machine.py`: `SystemState` + deterministic transitions.

- `__init__.py`: public exports.

## Recommended Flow
1. Evaluate fault condition (`FAULT` has priority).

2. Evaluate alert threshold (`ALERT`).

3. If there is low activity, go through `TRIGGERED` and `SCANNING`.

4. If there is no activity, return to `IDLE`.

## Exit Criteria (DoD)
- Explicit and serializable states.

- Clear, unambiguous transitions.

- Events usable by Layer 7 for notification.