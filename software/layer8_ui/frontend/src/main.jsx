import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const SENSORS = ["webcam", "thermal", "mmwave"];
const MODES = ["central", "fallback", "local"];
const TRACK_HISTORY_LIMIT = 18;
const FIELD_DEFS = {
  webcam: [
    "frames",
    "fps",
    "video",
    "live_frame",
    "webcam_device",
    "webcam_width",
    "webcam_height",
    "metrics_json",
    "weapon_unsafe_threshold",
    "weapon_gun_threshold",
    "weapon_yolo_model",
    "weapon_conf",
    "weapon_gun_imgsz",
    "weapon_extra_args"
  ],
  thermal: [
    "frames",
    "fps",
    "video",
    "live_frame",
    "thermal_device",
    "thermal_width",
    "thermal_height",
    "thermal_fps",
    "thermal_inference_enabled",
    "thermal_inference_threshold"
  ],
  mmwave: [
    "frames",
    "mmwave_only",
    "config",
    "cli_port",
    "data_port",
    "video",
    "live_frame",
    "output",
    "no_frame_timeout_s",
    "projection_width",
    "projection_height",
    "projection_x_scale_px_per_m",
    "projection_y_scale_px_per_m",
    "projection_x_offset_px",
    "projection_y_offset_px",
    "projection_rotation_deg",
    "projection_max_range_m",
    "mode",
    "extra_args"
  ]
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(payload.error || payload.detail || `Request failed: ${path}`);
  }
  return payload;
}

function usePolling() {
  const [config, setConfig] = useState(null);
  const [status, setStatus] = useState({});
  const [metrics, setMetrics] = useState({});
  const [devices, setDevices] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [overlay, setOverlay] = useState({ points: [] });
  const [mmwaveLatest, setMmwaveLatest] = useState(null);
  const [operatorState, setOperatorState] = useState({});
  const [error, setError] = useState("");
  const [lastRefreshMs, setLastRefreshMs] = useState(0);

  async function refresh() {
    try {
      const [st, mt, dv, al, ov, mw, op] = await Promise.all([
        api("/api/status"),
        api("/api/dashboard/metrics"),
        api("/api/devices"),
        api("/api/alerts/recent?limit=8"),
        api("/api/mmwave/camera-overlay"),
        api("/api/mmwave/latest"),
        api("/api/operator/state")
      ]);
      setStatus(st);
      setMetrics(mt);
      setDevices(dv.devices || []);
      setAlerts(al.alerts || []);
      setOverlay(ov);
      setMmwaveLatest(mw);
      setOperatorState(op);
      setLastRefreshMs(Date.now());
      setError("");
    } catch (err) {
      setError(String(err.message || err));
    }
  }

  useEffect(() => {
    api("/api/config").then(setConfig).catch((err) => setError(String(err.message || err)));
    refresh();
    const timer = window.setInterval(refresh, 1500);
    return () => window.clearInterval(timer);
  }, []);

  return { config, setConfig, status, metrics, devices, alerts, overlay, mmwaveLatest, operatorState, error, lastRefreshMs, refresh };
}

function StatusBadge({ status }) {
  return <span className={`badge ${status || "offline"}`}>{status || "offline"}</span>;
}

function DeviceGrid({ devices }) {
  return (
    <section className="panel">
      <header>Devices</header>
      <div className="device-grid">
        {devices.map((device) => (
          <article className="device-card" key={device.id}>
            <div>
              <strong>{device.label}</strong>
              <small>{device.kind} / {device.detail || "idle"}</small>
            </div>
            <StatusBadge status={device.status} />
          </article>
        ))}
      </div>
    </section>
  );
}

function MetricsPanel({ metrics, status, mmwaveLatest }) {
  const unsafe = metrics.unsafe_pct != null ? `${metrics.unsafe_pct}%` : "--";
  const state = status.state || "IDLE";
  const objectCount = mmwaveLatest?.object_count ?? 0;
  return (
    <section className="panel">
      <header>Operational Metrics</header>
      <div className="metrics-grid">
        <Metric label="State" value={state} />
        <Metric label="Unsafe" value={unsafe} danger={String(state).includes("ANOMALY")} />
        <Metric label="Gun detected" value={metrics.gun_detected == null ? "--" : metrics.gun_detected ? "yes" : "no"} />
        <Metric label="mmWave objects" value={objectCount} />
        <Metric label="Fused score" value={Number(status.fused_score || 0).toFixed(2)} />
        <Metric label="Sensors online" value={status.health?.sensor_online_count ?? 0} />
      </div>
    </section>
  );
}

function OperatorStatePanel({ operatorState, lastRefreshMs, onSetMode }) {
  const ageSec = lastRefreshMs ? Math.max(0, Math.round((Date.now() - lastRefreshMs) / 1000)) : "--";
  return (
    <section className="panel">
      <header>Operator State</header>
      <div className="operator-state">
        <Metric label="Mode" value={operatorState.mode || "central"} />
        <Metric label="Recovery" value={operatorState.recovery_state || "unknown"} danger={operatorState.has_fault} />
        <Metric label="Reconnect" value={`${ageSec}s ago`} />
        <Metric label="Online" value={operatorState.sensor_online_count ?? 0} />
      </div>
      <div className="mode-row">
        {MODES.map((mode) => (
          <button key={mode} className={operatorState.mode === mode ? "active" : ""} onClick={() => onSetMode(mode)}>
            {mode}
          </button>
        ))}
      </div>
    </section>
  );
}

function Metric({ label, value, danger = false }) {
  return (
    <div className={`metric ${danger ? "danger" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function LiveView({ overlay }) {
  const [source, setSource] = useState("webcam");
  const [history, setHistory] = useState({});
  const src = source === "webcam" ? "/api/preview/live/webcam" : "/api/preview/live/thermal";

  useEffect(() => {
    const points = overlay.points || [];
    if (!points.length) return;
    setHistory((current) => {
      const next = { ...current };
      points.forEach((point, index) => {
        const id = point.track_id || `R${index + 1}`;
        const entry = {
          x: Math.max(0, Math.min(1, Number(point.x_norm || 0))),
          y: Math.max(0, Math.min(1, Number(point.y_norm || 0)))
        };
        next[id] = [...(next[id] || []), entry].slice(-TRACK_HISTORY_LIMIT);
      });
      return next;
    });
  }, [overlay]);

  return (
    <section className="live-panel">
      <div className="live-head">
        <span>Live View</span>
        <div className="segmented">
          <button className={source === "webcam" ? "active" : ""} onClick={() => setSource("webcam")}>Webcam</button>
          <button className={source === "thermal" ? "active" : ""} onClick={() => setSource("thermal")}>Thermal</button>
        </div>
      </div>
      <div className="video-shell">
        <img src={`${src}?t=${Date.now()}`} alt={`${source} live feed`} />
        {source === "webcam" && <RadarOverlay overlay={overlay} history={history} />}
      </div>
    </section>
  );
}

function RadarOverlay({ overlay, history }) {
  return (
    <div className="radar-overlay">
      <svg className="trail-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {Object.entries(history || {}).map(([id, points]) => {
          if (!Array.isArray(points) || points.length < 2) return null;
          const d = points.map((p, idx) => `${idx === 0 ? "M" : "L"} ${p.x * 100} ${p.y * 100}`).join(" ");
          return <path key={id} d={d} />;
        })}
      </svg>
      {(overlay.points || []).slice(0, 64).map((point, index) => {
        const left = `${Math.max(0, Math.min(1, Number(point.x_norm || 0))) * 100}%`;
        const top = `${Math.max(0, Math.min(1, Number(point.y_norm || 0))) * 100}%`;
        return (
          <React.Fragment key={`${index}-${left}-${top}`}>
            <span className={`radar-dot ${Number(point.confidence || 0) >= 0.7 ? "unsafe" : ""}`} style={{ left, top }} />
            <span className="radar-label" style={{ left, top }}>{point.track_id || `R${index + 1}`}</span>
          </React.Fragment>
        );
      })}
    </div>
  );
}

function MmwavePanel({ latest, onRegenerate }) {
  return (
    <section className="panel">
      <header>mmWave Visualization</header>
      <div className="mmwave-preview">
        <img src={`/api/preview/live/mmwave?t=${Date.now()}`} alt="mmWave top-down preview" />
      </div>
      <div className="panel-actions">
        <button onClick={onRegenerate}>Regenerate preview</button>
        <a href="/api/preview/output/mmwave" target="_blank" rel="noreferrer">JSON</a>
      </div>
      <pre className="mini-json">{JSON.stringify(latest || {}, null, 2)}</pre>
    </section>
  );
}

function AlertsPanel({ alerts }) {
  return (
    <section className="panel">
      <header>Alerts</header>
      <div className="alerts">
        {alerts.map((alert) => (
          <article className="alert-row" key={alert.event_id}>
            <strong>{alert.message || alert.state || "Alert"}</strong>
            <small>{alert.level || "info"} / {alert.radar_id || "system"}</small>
          </article>
        ))}
      </div>
    </section>
  );
}

function ControlsPanel({ config, setConfig, onRefresh }) {
  const [active, setActive] = useState("mmwave");
  const section = config?.[active] || {};
  const fields = FIELD_DEFS[active] || [];

  function updateField(key, value) {
    setConfig((current) => ({
      ...current,
      [active]: {
        ...(current?.[active] || {}),
        [key]: value
      }
    }));
  }

  async function save() {
    await api("/api/config", {
      method: "PUT",
      body: JSON.stringify({ settings: config })
    });
    await onRefresh();
  }

  async function action(name) {
    await api(`/api/${name}/${active}`, { method: "POST" });
    await onRefresh();
  }

  return (
    <section className="panel controls">
      <header>Controls</header>
      <div className="tabs">
        {SENSORS.map((sensor) => (
          <button key={sensor} className={active === sensor ? "active" : ""} onClick={() => setActive(sensor)}>
            {sensor === "mmwave" ? "mmWave" : sensor}
          </button>
        ))}
      </div>
      <div className="control-actions">
        <button className="primary" onClick={() => action("run")}>Run</button>
        <button onClick={() => action("stop")}>Stop</button>
        <button onClick={() => action("restart")}>Restart</button>
        <button onClick={save}>Save config</button>
      </div>
      <div className="field-grid">
        {fields.map((key) => (
          <label key={key}>
            <span>{key}</span>
            <input
              value={section[key] ?? ""}
              onChange={(event) => updateField(key, coerceFieldValue(section[key], event.target.value))}
            />
          </label>
        ))}
      </div>
    </section>
  );
}

function coerceFieldValue(previous, raw) {
  if (typeof previous === "number") {
    const value = Number(raw);
    return Number.isFinite(value) ? value : 0;
  }
  return raw;
}

function App() {
  const { config, setConfig, status, metrics, devices, alerts, overlay, mmwaveLatest, operatorState, error, lastRefreshMs, refresh } = usePolling();
  const ready = useMemo(() => Boolean(config), [config]);

  async function regeneratePreview() {
    await api("/api/mmwave/preview/regenerate", { method: "POST" });
    await refresh();
  }

  async function setMode(mode) {
    await api(`/api/operator/mode/${mode}`, { method: "POST" });
    await refresh();
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>SCANU Operations</h1>
          <p>Layer 8 React control panel</p>
        </div>
        <div className="top-actions">
          <button onClick={() => api("/api/run_all", { method: "POST" }).then(refresh)}>Run all</button>
          <button onClick={() => api("/api/stop_all", { method: "POST" }).then(refresh)}>Stop all</button>
          <button onClick={refresh}>Refresh</button>
        </div>
      </header>
      {error && <div className="banner">{error}</div>}
      <section className="main-grid">
        <div className="left-stack">
          <MetricsPanel metrics={metrics} status={status} mmwaveLatest={mmwaveLatest} />
          <OperatorStatePanel operatorState={operatorState} lastRefreshMs={lastRefreshMs} onSetMode={setMode} />
          <DeviceGrid devices={devices} />
          <AlertsPanel alerts={alerts} />
        </div>
        <LiveView overlay={overlay} />
        <div className="right-stack">
          <MmwavePanel latest={mmwaveLatest} onRegenerate={regeneratePreview} />
          {ready && <ControlsPanel config={config} setConfig={setConfig} onRefresh={refresh} />}
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
