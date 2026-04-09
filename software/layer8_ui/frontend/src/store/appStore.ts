import type {
  AlertPayload,
  AppState,
  ConnectionState,
  ConsoleMode,
  ControlResult,
  HealthResponse,
  ScorePoint,
  SensorStatus,
  SensorFaultPayload,
  StatusPayload,
  SystemState,
  VisualPayload,
} from "../types";
import { clamp } from "../lib/utils";

const DEFAULT_STATUS: StatusPayload = {
  state: "UNKNOWN",
  dwell_ms: 0,
  fused_score: 0,
  confidence: 0,
  health: {
    has_fault: false,
    fault_code: null,
    sensor_online_count: 0,
  },
  active_radars: [],
  updated_at_utc: null,
  latest_alert: null,
};

const DEFAULT_HEALTH: HealthResponse = {
  healthy: false,
  has_fault: false,
  fault_code: null,
  sensor_online_count: 0,
  state: "UNKNOWN",
  updated_at_utc: null,
};

const DEFAULT_VISUAL: VisualPayload = {
  timestamp_ms: null,
  source_mode: "none",
  rgb_jpeg_b64: null,
  thermal_jpeg_b64: null,
  point_cloud: [],
  presence: null,
  meta: { ready: false },
};

export function createInitialState(): AppState {
  return {
    mode: "monitor",
    connection: "offline",
    lastHeartbeatMs: null,
    lastWsMessageMs: null,
    status: DEFAULT_STATUS,
    health: DEFAULT_HEALTH,
    sensors: [],
    alerts: [],
    controlResults: [],
    scoreHistory: [],
    lastSensorFault: null,
    visual: DEFAULT_VISUAL,
  };
}

export type AppAction =
  | { type: "SET_MODE"; mode: ConsoleMode }
  | { type: "SET_CONNECTION"; connection: ConnectionState }
  | { type: "UPSERT_STATUS"; status: StatusPayload; ts: number }
  | { type: "SET_HEALTH"; health: HealthResponse }
  | { type: "SET_SENSORS"; sensors: SensorStatus[] }
  | { type: "UPSERT_SENSOR"; sensor: SensorStatus }
  | { type: "SET_ALERTS"; alerts: AlertPayload[] }
  | { type: "ADD_ALERT"; alert: AlertPayload }
  | { type: "ADD_CONTROL_RESULT"; result: ControlResult }
  | { type: "SET_SENSOR_FAULT"; payload: SensorFaultPayload | null }
  | { type: "SET_VISUAL"; visual: VisualPayload }
  | { type: "HEARTBEAT"; ts: number }
  | { type: "WS_MESSAGE"; ts: number };

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "SET_MODE":
      return { ...state, mode: action.mode };
    case "SET_CONNECTION":
      return { ...state, connection: action.connection };
    case "UPSERT_STATUS": {
      const nextStatus = normalizeStatus(action.status);
      const nextHistory = appendScore(state.scoreHistory, nextStatus, action.ts);
      return { ...state, status: nextStatus, scoreHistory: nextHistory };
    }
    case "SET_HEALTH":
      return { ...state, health: action.health };
    case "SET_SENSORS":
      return { ...state, sensors: action.sensors };
    case "UPSERT_SENSOR": {
      const filtered = state.sensors.filter((s) => s.radar_id !== action.sensor.radar_id);
      return {
        ...state,
        sensors: [...filtered, action.sensor].sort((a, b) => a.radar_id.localeCompare(b.radar_id)),
      };
    }
    case "SET_ALERTS":
      return { ...state, alerts: action.alerts };
    case "ADD_ALERT": {
      const deduped = [action.alert, ...state.alerts.filter((a) => a.event_id !== action.alert.event_id)];
      return { ...state, alerts: deduped.slice(0, 200) };
    }
    case "ADD_CONTROL_RESULT":
      return { ...state, controlResults: [action.result, ...state.controlResults].slice(0, 200) };
    case "SET_SENSOR_FAULT":
      return { ...state, lastSensorFault: action.payload };
    case "SET_VISUAL":
      return { ...state, visual: action.visual };
    case "HEARTBEAT":
      return { ...state, lastHeartbeatMs: action.ts };
    case "WS_MESSAGE":
      return { ...state, lastWsMessageMs: action.ts };
    default:
      return state;
  }
}

function appendScore(history: ScorePoint[], status: StatusPayload, ts: number): ScorePoint[] {
  const point: ScorePoint = {
    ts,
    score: clamp(status.fused_score),
    state: status.state,
  };
  const all = [...history, point];
  const minTs = ts - 120_000;
  return all.filter((p) => p.ts >= minTs);
}

export function normalizeStatus(raw: Partial<StatusPayload>): StatusPayload {
  const state = (raw.state ?? "UNKNOWN") as SystemState;
  const health = raw.health ?? DEFAULT_STATUS.health;
  return {
    state,
    dwell_ms: Number(raw.dwell_ms ?? 0),
    fused_score: Number(raw.fused_score ?? 0),
    confidence: Number(raw.confidence ?? 0),
    health: {
      has_fault: Boolean(health.has_fault),
      fault_code: (health.fault_code as string | null) ?? null,
      sensor_online_count: Number(health.sensor_online_count ?? 0),
    },
    active_radars: Array.isArray(raw.active_radars) ? raw.active_radars.map(String) : [],
    updated_at_utc: raw.updated_at_utc ?? null,
    latest_alert: raw.latest_alert ?? null,
  };
}
