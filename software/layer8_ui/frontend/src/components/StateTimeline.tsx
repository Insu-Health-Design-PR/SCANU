import type { ScorePoint } from "../types";
import { STATE_COLORS } from "../lib/utils";

export function StateTimeline({ points }: { points: ScorePoint[] }) {
  const recent = points.slice(-30);
  return (
    <section className="panel">
      <h3>State Timeline</h3>
      <div className="timeline">
        {recent.length === 0 && <span className="muted">No state samples yet.</span>}
        {recent.map((item, idx) => (
          <div key={`${item.ts}-${idx}`} className="timeline-item" title={`${item.state} @ ${new Date(item.ts).toLocaleTimeString()}`}>
            <span className="dot" style={{ backgroundColor: STATE_COLORS[item.state] }} />
            <small>{item.state}</small>
          </div>
        ))}
      </div>
    </section>
  );
}
