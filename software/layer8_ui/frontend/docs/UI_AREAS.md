# Exact UI Requirements by Area

## 1. Top Bar
### Must show
- Product title: SCAN-U Monitor
- Global health badge
- Live/simulated mode
- View Layout trigger
- Optional timestamp / environment label

### Must do
- Open layout selector
- Surface current selected layout mode
- Keep status readable without taking too much space

## 2. RGB Camera Area
### Must show
- Header title
- Primary visual stream
- Stream metadata: resolution, fps, stream status, latency

### Must do
- Act as one of the main visual anchors
- Support future fullscreen or focus expansion

## 3. Thermal Camera Area
### Must show
- Header title
- Thermal styled display
- Palette/fps/stream status metadata

### Must do
- Sit parallel to RGB in default mode
- Support focus mode later

## 4. Point Cloud Area
### Must show
- Spatial radar scene
- Tracked points count
- Confidence
- Last update

### Must do
- Be a primary area, not a side widget
- Look more advanced than a simple chart

## 5. Presence Sensor Area
### Must show
- Presence detected or not
- Confidence percent
- Small sparkline / mini trend
- Last trigger timestamp

### Must do
- Stay clearly secondary
- Never become a fourth equal main panel

## 6. System Status Area
### Must show
- Connected
- Configured
- Streaming
- Current state
- Fused score
- Active sensors

### Must do
- Help operator judge readiness instantly

## 7. Execution Controls Area
### Must show
- Start
- Stop
- Reconfigure
- Reset
- Record Session
- Mode switch

### Must do
- Be visually real but decoupled from backend for now

## 8. Console Log Area
### Must show
- Timestamped entries
- Severity
- Human-readable system messages

### Must do
- Stay compact
- Support future streaming logs via WebSocket

## 9. Layout System
### Must show
- Mini popover
- Presets
- Open Preview CTA
- Large modal preview
- Apply Layout action

### Must do
- Prevent abrupt layout jumps
- Let the operator preview before applying
