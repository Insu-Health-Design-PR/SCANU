import type { ControlResult } from "../types";

export function ControlLogPanel({ results }: { results: ControlResult[] }) {
  return (
    <section className="panel">
      <h3>Control Output</h3>
      <div className="control-log">
        {results.length === 0 && <div className="muted">No control operations yet.</div>}
        {results.map((r, idx) => (
          <div key={`${r.radar_id}-${r.action}-${idx}`} className={`log-row ${r.success ? "ok" : "bad"}`}>
            <div>
              <strong>{r.action}</strong> on <b>{r.radar_id}</b>
            </div>
            <div>{r.message}</div>
            <pre>{JSON.stringify(r.details, null, 2)}</pre>
          </div>
        ))}
      </div>
    </section>
  );
}
