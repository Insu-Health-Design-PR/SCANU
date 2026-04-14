export type SystemState = 'UNKNOWN' | 'IDLE' | 'TRIGGERED' | 'SCANNING' | 'ALERT' | 'FAULT';
export type DashboardMode = 'live' | 'simulated';
export type FeedSource = 'live';

export interface RenderPoint {
  id: number;
  left: string;
  top: string;
  size: string;
  opacity: number;
}

export interface CameraStream {
  label: string;
  resolution: string;
  fps: number;
  status: 'streaming' | 'paused' | 'fault';
  latencyMs: number;
  frameBase64?: string | null;
  source: FeedSource;
  stale: boolean;
  lastFrameAtMs: number;
}

export interface PointCloudSnapshot {
  trackedPoints: number;
  confidence: number;
  lastUpdateMs: number;
  updateRateHz: number;
  source: FeedSource;
  stale: boolean;
  lastFrameAtMs: number;
  renderPoints: RenderPoint[];
}

export interface PresenceSnapshot {
  detected: boolean;
  confidence: number;
  lastTriggerIso: string;
  timeline: number[];
}

export interface HealthSnapshot {
  connected: boolean;
  configured: boolean;
  streaming: boolean;
  healthy: boolean;
  activeSensors: number;
  sensorCount: number;
  fusedScore: number;
  confidence: number;
}

export interface AlertRecord {
  id: string;
  level: 'info' | 'warning' | 'fault';
  timestamp: string;
  message: string;
}

export interface DashboardSnapshot {
  mode: DashboardMode;
  state: SystemState;
  health: HealthSnapshot;
  rgb: CameraStream;
  thermal: CameraStream;
  pointCloud: PointCloudSnapshot;
  presence: PresenceSnapshot;
  alerts: AlertRecord[];
}
