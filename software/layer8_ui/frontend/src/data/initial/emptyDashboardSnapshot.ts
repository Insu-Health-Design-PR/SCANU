import type { DashboardSnapshot } from '@/types/domain';

function emptyTimeline(size = 30): number[] {
  return Array.from({ length: size }, () => 0);
}

const now = Date.now();

export const emptyDashboardSnapshot: DashboardSnapshot = {
  mode: 'live',
  state: 'UNKNOWN',
  health: {
    connected: false,
    configured: false,
    streaming: false,
    healthy: false,
    activeSensors: 0,
    sensorCount: 0,
    fusedScore: 0,
    confidence: 0,
  },
  rgb: {
    label: 'RGB Camera',
    resolution: '1080p',
    fps: 30,
    status: 'paused',
    latencyMs: 0,
    frameBase64: null,
    source: 'live',
    stale: true,
    lastFrameAtMs: now,
  },
  thermal: {
    label: 'Thermal Camera',
    resolution: '640x480',
    fps: 30,
    status: 'paused',
    latencyMs: 0,
    frameBase64: null,
    source: 'live',
    stale: true,
    lastFrameAtMs: now,
  },
  pointCloud: {
    trackedPoints: 0,
    confidence: 0,
    lastUpdateMs: 0,
    updateRateHz: 0,
    source: 'live',
    stale: true,
    lastFrameAtMs: now,
    renderPoints: [],
  },
  presence: {
    detected: false,
    confidence: 0,
    lastTriggerIso: '',
    timeline: emptyTimeline(),
  },
  alerts: [],
};
