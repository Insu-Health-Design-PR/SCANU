# Future Data Contracts

## DashboardSnapshot
```ts
interface DashboardSnapshot {
  timestamp: string;
  mode: 'live' | 'simulated';
  state: SystemState;
  health: HealthSnapshot;
  cameras: CameraStreams;
  pointCloud: PointCloudSnapshot;
  presence: PresenceSnapshot;
  alerts: AlertRecord[];
}
```

## HealthSnapshot
```ts
interface HealthSnapshot {
  connected: boolean;
  configured: boolean;
  streaming: boolean;
  healthy: boolean;
  activeSensors: number;
  sensorCount: number;
  fusedScore: number;
  confidence: number;
}
```

## PointCloudSnapshot
```ts
interface PointCloudSnapshot {
  trackedPoints: number;
  updateRateHz: number;
  confidence: number;
  lastUpdateMs: number;
}
```

## PresenceSnapshot
```ts
interface PresenceSnapshot {
  detected: boolean;
  confidence: number;
  lastTriggerIso: string;
  timeline: number[];
}
```

## AlertRecord
```ts
interface AlertRecord {
  id: string;
  level: 'info' | 'warning' | 'fault';
  timestamp: string;
  message: string;
}
```
