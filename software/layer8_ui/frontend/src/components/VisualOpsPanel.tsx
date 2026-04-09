import type { PointCloudPoint, VisualPayload } from "../types";

function pointToXY(p: PointCloudPoint, width: number, height: number): { x: number; y: number } {
  const xNorm = Math.max(-1, Math.min(1, p.x / 2));
  const yNorm = Math.max(0, Math.min(1, p.y / 6));
  return {
    x: (xNorm * 0.5 + 0.5) * width,
    y: height - yNorm * height,
  };
}

function imageSrc(encoded: string | null): string | null {
  if (!encoded) return null;
  return `data:image/jpeg;base64,${encoded}`;
}

export function VisualOpsPanel({ visual }: { visual: VisualPayload }) {
  const rgbSrc = imageSrc(visual.rgb_jpeg_b64);
  const thermalSrc = imageSrc(visual.thermal_jpeg_b64);

  return (
    <section className="panel">
      <h3>Visual Monitor</h3>
      <div className="muted">source: {visual.source_mode}</div>

      <div className="visual-grid">
        <div className="visual-card">
          <h4>RGB Camera</h4>
          {rgbSrc ? <img src={rgbSrc} alt="RGB sensor stream" className="visual-img" /> : <div className="placeholder">RGB unavailable</div>}
        </div>

        <div className="visual-card">
          <h4>Thermal Camera</h4>
          {thermalSrc ? (
            <img src={thermalSrc} alt="Thermal sensor stream" className="visual-img" />
          ) : (
            <div className="placeholder">Thermal unavailable</div>
          )}
        </div>

        <div className="visual-card">
          <h4>Point Cloud</h4>
          <svg className="point-cloud-svg" viewBox="0 0 360 220" role="img" aria-label="Point cloud view">
            <rect x="0" y="0" width="360" height="220" fill="#0e141c" />
            <line x1="180" y1="0" x2="180" y2="220" stroke="#2a384b" strokeWidth="1" />
            <line x1="0" y1="219" x2="360" y2="219" stroke="#2a384b" strokeWidth="1" />
            {visual.point_cloud.map((p, idx) => {
              const pos = pointToXY(p, 360, 220);
              const r = Math.max(2, Math.min(4, p.snr / 5));
              return <circle key={idx} cx={pos.x} cy={pos.y} r={r} fill="#58c9ff" opacity="0.85" />;
            })}
          </svg>
          <div className="muted">points: {visual.point_cloud.length}</div>
        </div>

        <div className="visual-card">
          <h4>Presence Sensor</h4>
          {visual.presence ? (
            <div className="stats-grid">
              <div>
                <label>presence_raw</label>
                <strong>{visual.presence.presence_raw.toFixed(3)}</strong>
              </div>
              <div>
                <label>motion_raw</label>
                <strong>{visual.presence.motion_raw.toFixed(3)}</strong>
              </div>
              <div>
                <label>distance_m</label>
                <strong>{visual.presence.distance_m == null ? "-" : visual.presence.distance_m.toFixed(2)}</strong>
              </div>
            </div>
          ) : (
            <div className="placeholder">Presence unavailable</div>
          )}
        </div>
      </div>
    </section>
  );
}
