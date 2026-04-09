import type { ScorePoint } from "../types";

export function ScoreTrendChart({ points }: { points: ScorePoint[] }) {
  const width = 860;
  const height = 180;
  const pad = 20;

  if (points.length < 2) {
    return (
      <section className="panel">
        <h3>Score Trend (120s)</h3>
        <div className="placeholder">Waiting for enough samples.</div>
      </section>
    );
  }

  const firstTs = points[0].ts;
  const lastTs = points[points.length - 1].ts;
  const dt = Math.max(lastTs - firstTs, 1);

  const path = points
    .map((p, idx) => {
      const x = pad + ((p.ts - firstTs) / dt) * (width - pad * 2);
      const y = height - pad - p.score * (height - pad * 2);
      return `${idx === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <section className="panel">
      <h3>Score Trend (120s)</h3>
      <svg viewBox={`0 0 ${width} ${height}`} className="score-chart" role="img" aria-label="Score trend chart">
        <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} className="axis" />
        <line x1={pad} y1={pad} x2={pad} y2={height - pad} className="axis" />
        <path d={path} className="score-path" />
      </svg>
      <div className="heatmap-placeholder">Heatmap pending Layer 3/4 output contract.</div>
    </section>
  );
}
