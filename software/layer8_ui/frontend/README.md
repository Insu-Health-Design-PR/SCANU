# SCAN-U Layer 8 UI Scaffold

This package is a **frontend scaffold for `software/layer8_ui`**.
It is intentionally aligned with the SCAN-U architecture where Layer 8 is the dashboard/UI layer, and upstream layers provide fusion results, state transitions, and alert/event history.

## Goals
- Modern React + TypeScript UI
- Premium dark visual language inspired by the approved mockup
- Clear separation between:
  - RGB camera
  - Thermal camera
  - Point cloud
  - Presence sensor
  - System status
  - Execution controls
  - Console log
- Layout switcher with preview modal
- Easy future connection to FastAPI / WebSocket backend

## Reference alignment
This scaffold was shaped from:
- Project checklist requesting a web dashboard, heatmap visualization, anomaly score meter, and timestamped alert log.
- Development plan stating Layer 8 uses React and should display live heatmap, anomaly score graph, sensor health, and trigger log.
- Layer 5/6/7 contracts, where UI should eventually consume fusion outputs, state transitions, and event records.

## Suggested repo placement
Copy this folder into:

```bash
software/layer8_ui
```

## Run locally
```bash
npm install
npm run dev
```

## Main areas
- `docs/` architecture and exact UI requirements by area
- `src/components/` UI components by responsibility
- `src/data/mock/` realistic mock data
- `src/services/` adapters for future backend integration
- `src/types/` typed contracts for the dashboard domain
