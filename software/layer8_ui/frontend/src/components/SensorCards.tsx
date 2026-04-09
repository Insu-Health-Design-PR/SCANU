import type { ConsoleMode, SensorStatus } from "../types";

export type SensorAction = "status" | "reconfig" | "reset_soft" | "kill_holders" | "usb_reset";

function actionAllowed(mode: ConsoleMode, action: SensorAction): boolean {
  if (mode === "monitor") return false;
  if (mode === "control") {
    return action === "status" || action === "reconfig" || action === "reset_soft";
  }
  return true;
}

export function SensorCards({
  sensors,
  mode,
  onAction,
}: {
  sensors: SensorStatus[];
  mode: ConsoleMode;
  onAction: (sensor: SensorStatus, action: SensorAction) => void;
}) {
  return (
    <section className="panel">
      <h3>Sensors</h3>
      <div className="sensor-grid">
        {sensors.map((sensor) => (
          <article key={sensor.radar_id} className="sensor-card">
            <header>
              <h4>{sensor.radar_id}</h4>
            </header>
            <div className="sensor-values">
              <span>connected: {String(sensor.connected)}</span>
              <span>configured: {String(sensor.configured)}</span>
              <span>streaming: {String(sensor.streaming)}</span>
              <span>fault: {sensor.fault_code ?? "-"}</span>
              <span>last_seen_ms: {sensor.last_seen_ms ?? "-"}</span>
            </div>
            <div className="sensor-actions">
              {(["status", "reconfig", "reset_soft", "kill_holders", "usb_reset"] as SensorAction[]).map((action) => (
                <button
                  key={action}
                  className={`btn ${action.includes("reset") || action.includes("kill") ? "warn" : ""}`}
                  disabled={!actionAllowed(mode, action)}
                  onClick={() => onAction(sensor, action)}
                >
                  {action}
                </button>
              ))}
            </div>
          </article>
        ))}
        {sensors.length === 0 && <div className="muted">No sensor status yet.</div>}
      </div>
    </section>
  );
}
