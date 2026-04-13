import type { DashboardSnapshot } from '@/types/domain';

export const dashboardSnapshot: DashboardSnapshot = {
  mode: 'live',
  state: 'SCANNING',
  health: {
    connected: true,
    configured: true,
    streaming: true,
    healthy: true,
    activeSensors: 4,
    sensorCount: 4,
    fusedScore: 0.89,
    confidence: 0.86,
  },
  rgb: {
    label: 'RGB Camera',
    resolution: '1080p',
    fps: 30,
    status: 'streaming',
    latencyMs: 24,
  },
  thermal: {
    label: 'Thermal Camera',
    resolution: '640x480',
    fps: 30,
    status: 'streaming',
    latencyMs: 18,
  },
  pointCloud: {
    trackedPoints: 159,
    confidence: 0.89,
    lastUpdateMs: 800,
    updateRateHz: 14,
  },
  presence: {
    detected: true,
    confidence: 0.94,
    lastTriggerIso: '2026-04-10T10:45:00Z',
    timeline: [18, 20, 24, 22, 26, 29, 32, 31, 38, 40, 42, 45, 47, 48, 50, 52, 51, 49, 46, 44, 40, 42, 45, 47, 48, 52, 55, 57, 58, 59],
  },
  alerts: [
    { id: '1', level: 'info', timestamp: '10:45:00', message: 'Presence trigger detected. Confidence 54%.' },
    { id: '2', level: 'info', timestamp: '10:43:21', message: 'Streams synchronized across RGB, thermal, radar, and presence modules.' },
    { id: '3', level: 'info', timestamp: '10:43:05', message: 'System configured. Ready.' },
    { id: '4', level: 'fault', timestamp: '10:42:55', message: 'Temporary latency spike corrected.' },
    { id: '5', level: 'info', timestamp: '10:42:45', message: 'Anomaly score updated. Confidence 86%.' },
  ],
};
