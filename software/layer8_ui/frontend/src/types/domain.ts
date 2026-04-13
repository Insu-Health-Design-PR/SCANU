export type SystemState = 'IDLE' | 'TRIGGERED' | 'SCANNING' | 'ALERT' | 'FAULT';
export type DashboardMode = 'live' | 'simulated';

export interface CameraStream {
  label: string;
  resolution: string;
  fps: number;
  status: 'streaming' | 'paused' | 'fault';
  latencyMs: number;
}

export interface PointCloudSnapshot {
  trackedPoints: number;
  confidence: number;
  lastUpdateMs: number;
  updateRateHz: number;
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
