export type SystemState =
  | "UNKNOWN"
  | "IDLE"
  | "TRIGGERED"
  | "SCANNING"
  | "ANOMALY_DETECTED"
  | "FAULT";

export type AlertLevel = "INFO" | "WARNING" | "ALERT" | "FAULT";

export type ConsoleMode = "monitor" | "control" | "maintenance";

export type ConnectionState = "connected" | "degraded" | "offline";

export interface HealthPayload {
  has_fault: boolean;
  fault_code: string | null;
  sensor_online_count: number;
  [k: string]: unknown;
}

export interface StatusPayload {
  state: SystemState;
  dwell_ms: number;
  fused_score: number;
  confidence: number;
  health: HealthPayload;
  active_radars: string[];
  updated_at_utc?: string | null;
  latest_alert?: AlertPayload | null;
}

export interface HealthResponse {
  healthy: boolean;
  has_fault: boolean;
  fault_code: string | null;
  sensor_online_count: number;
  state: SystemState;
  updated_at_utc: string | null;
}

export interface AlertPayload {
  event_id: string;
  timestamp_utc: string;
  level: AlertLevel;
  state: SystemState;
  message: string;
  radar_id: string;
  scores: Record<string, number>;
  metadata: Record<string, unknown>;
}

export interface SensorStatus {
  radar_id: string;
  connected: boolean;
  configured: boolean;
  streaming: boolean;
  fault_code: string | null;
  last_seen_ms: number | null;
  config_port?: string | null;
  data_port?: string | null;
}

export interface ControlResult {
  radar_id: string;
  action: string;
  success: boolean;
  message: string;
  details: Record<string, unknown>;
}

export interface SensorFaultPayload {
  radars: string[];
  fault_code: string | null;
  action_request?: {
    action: string;
    reason: string;
    manual_required: boolean;
  };
}

export interface ScorePoint {
  ts: number;
  score: number;
  state: SystemState;
}

export interface AppState {
  mode: ConsoleMode;
  connection: ConnectionState;
  lastHeartbeatMs: number | null;
  lastWsMessageMs: number | null;
  status: StatusPayload;
  health: HealthResponse;
  sensors: SensorStatus[];
  alerts: AlertPayload[];
  controlResults: ControlResult[];
  scoreHistory: ScorePoint[];
  lastSensorFault: SensorFaultPayload | null;
}
