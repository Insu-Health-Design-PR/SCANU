# Layer 8 Frontend Architecture

## Purpose
Layer 8 is the operator-facing dashboard. It should visualize and control the SCAN-U system, not own the core detection logic.

## Responsibilities
- Render the main operator experience
- Present data from upstream layers
- Provide layout switching for demos and operations
- Display live and historical system feedback
- Surface health, state, and alerts in a readable way

## Upstream alignment
### Layer 5 Fusion
The UI will consume fused scores, evidence, and final trigger confidence.

### Layer 6 State Machine
The UI will show system states such as `IDLE`, `TRIGGERED`, `SCANNING`, `ALERT`, and `FAULT`.

### Layer 7 Alerts
The UI will render recent alerts and logs, and later acknowledge alert transport or delivery status.

## Layer 8 structure
- `src/pages/` page-level composition
- `src/components/layout/` dashboard shell, rail, modal composition
- `src/components/panels/` domain panels
- `src/components/view-layout/` layout selector and preview modal
- `src/data/mock/` fake but realistic data sources
- `src/services/` backend adapter boundary
- `src/store/` UI state and layout state
- `src/types/` typed contracts
- `src/lib/` utilities

## Architecture principles
- Presentational components stay dumb when possible
- State lives in one focused store for dashboard state
- API wiring goes through adapters, not directly from panels
- Each panel owns its rendering only
- Shared styles go through shared primitives
- All layout modes are declared from typed configuration, not scattered conditionals
