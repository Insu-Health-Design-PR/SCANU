import type { HealthResponse, StatusPayload } from "../types";
import { formatMs, formatTimeIso } from "../lib/utils";

export function GlobalStatusPanel({ status, health }: { status: StatusPayload; health: HealthResponse }) {
  return (
    <section className="panel">
      <h3>System Status</h3>
      <div className="stats-grid">
        <div>
          <label>State</label>
          <strong>{status.state}</strong>
        </div>
        <div>
          <label>Fused Score</label>
          <strong>{status.fused_score.toFixed(3)}</strong>
        </div>
        <div>
          <label>Confidence</label>
          <strong>{status.confidence.toFixed(3)}</strong>
        </div>
        <div>
          <label>Dwell</label>
          <strong>{formatMs(status.dwell_ms)}</strong>
        </div>
        <div>
          <label>Updated</label>
          <strong>{formatTimeIso(status.updated_at_utc)}</strong>
        </div>
      </div>
      <div className="chips">
        <span className={`chip ${health.healthy ? "ok" : "bad"}`}>{health.healthy ? "HEALTHY" : "UNHEALTHY"}</span>
        <span className={`chip ${health.has_fault ? "bad" : "ok"}`}>FAULT: {health.has_fault ? "YES" : "NO"}</span>
        <span className="chip">SENSORS: {health.sensor_online_count}</span>
        <span className="chip">FAULT CODE: {health.fault_code ?? "-"}</span>
      </div>
    </section>
  );
}
