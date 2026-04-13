import type { DashboardSnapshot, RenderPoint } from '@/types/domain';
import type { UiPreferences } from '@/types/layout';
import { dashboardSnapshot } from '@/data/mock/dashboardSnapshot';
import { pointCloudPoints } from '@/data/mock/pointCloud';

type AlertLevel = 'info' | 'warning' | 'fault';

interface BackendStatusResponse {
  state: string;
  fused_score: number;
  confidence: number;
  health: {
    has_fault?: boolean;
    sensor_online_count?: number;
  };
  active_radars?: string[];
}

interface BackendHealthResponse {
  healthy: boolean;
  has_fault: boolean;
  sensor_online_count: number;
}

interface BackendAlert {
  event_id?: string;
  level?: string;
  timestamp_utc?: string;
  message?: string;
}

interface BackendVisualLatest {
  timestamp_ms?: number | null;
  source_mode?: string;
  rgb_jpeg_b64?: string | null;
  thermal_jpeg_b64?: string | null;
  point_cloud?: unknown[];
  presence?: boolean | { detected?: boolean; confidence?: number } | null;
  meta?: Record<string, unknown>;
}

interface BackendWsEvent {
  event_type: string;
  payload: unknown;
}

interface ControlResult {
  radar_id?: string;
  action?: string;
  success?: boolean;
  reason?: string | null;
  details?: string | null;
}

const API_BASE = import.meta.env.VITE_LAYER8_API_BASE ?? 'http://127.0.0.1:8080';
const WS_EVENTS_URL =
  import.meta.env.VITE_LAYER8_WS_URL ?? `${API_BASE.replace(/^http/i, 'ws')}/ws/events`;
const PREFS_ENDPOINT = `${API_BASE}/api/ui/preferences`;

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${url}`);
  }
  return (await response.json()) as T;
}

async function postJson<T>(url: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${url}`);
  }
  return (await response.json()) as T;
}

function toAlertLevel(level: string | undefined): AlertLevel {
  if (level === 'fault') return 'fault';
  if (level === 'warning') return 'warning';
  return 'info';
}

function toRenderPoints(raw: unknown[]): RenderPoint[] {
  if (!Array.isArray(raw) || raw.length === 0) return pointCloudPoints;

  const parsed = raw
    .map((item, idx) => {
      if (!item || typeof item !== 'object') return null;
      const obj = item as Record<string, unknown>;
      const x =
        typeof obj.x === 'number'
          ? obj.x
          : typeof obj.x_m === 'number'
            ? obj.x_m
            : typeof obj.pos_x === 'number'
              ? obj.pos_x
              : null;
      const y =
        typeof obj.y === 'number'
          ? obj.y
          : typeof obj.y_m === 'number'
            ? obj.y_m
            : typeof obj.pos_y === 'number'
              ? obj.pos_y
              : null;
      const z =
        typeof obj.z === 'number'
          ? obj.z
          : typeof obj.z_m === 'number'
            ? obj.z_m
            : typeof obj.pos_z === 'number'
              ? obj.pos_z
              : 0;
      if (x === null || y === null) return null;
      return { idx, x, y, z };
    })
    .filter(Boolean) as Array<{ idx: number; x: number; y: number; z: number }>;

  if (parsed.length === 0) return pointCloudPoints;

  const xs = parsed.map((p) => p.x);
  const ys = parsed.map((p) => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const dx = maxX - minX || 1;
  const dy = maxY - minY || 1;

  return parsed.map((p) => {
    const nx = (p.x - minX) / dx;
    const ny = (p.y - minY) / dy;
    const depthInfluence = Math.max(0, Math.min(1, 1 - Math.abs(p.z) / 6));
    return {
      id: p.idx,
      left: `${8 + nx * 84}%`,
      top: `${10 + (1 - ny) * 74}%`,
      size: `${2 + depthInfluence * 3}px`,
      opacity: 0.3 + depthInfluence * 0.55,
    };
  });
}

function toDashboardSnapshot(
  status: BackendStatusResponse,
  health: BackendHealthResponse,
  alerts: BackendAlert[],
  visual: BackendVisualLatest,
): DashboardSnapshot {
  const sensorCount = Math.max(health.sensor_online_count || 0, status.active_radars?.length || 0, 1);
  const onlineCount = health.sensor_online_count || 0;
  const nowMs = Date.now();
  const timestampMs = visual.timestamp_ms ?? nowMs;
  const pointCloudRaw = Array.isArray(visual.point_cloud) ? visual.point_cloud : [];
  const detected =
    typeof visual.presence === 'boolean'
      ? visual.presence
      : typeof visual.presence === 'object' && visual.presence !== null
        ? Boolean(visual.presence.detected)
        : false;
  const presenceConfidence =
    typeof visual.presence === 'object' && visual.presence !== null && typeof visual.presence.confidence === 'number'
      ? visual.presence.confidence
      : detected
        ? 0.8
        : 0.0;

  const rgbHasFrame = Boolean(visual.rgb_jpeg_b64);
  const thermalHasFrame = Boolean(visual.thermal_jpeg_b64);

  return {
    mode: visual.source_mode === 'simulate' ? 'simulated' : 'live',
    state: (status.state ?? 'UNKNOWN') as DashboardSnapshot['state'],
    health: {
      connected: onlineCount > 0,
      configured: onlineCount > 0,
      streaming: onlineCount > 0,
      healthy: health.healthy && !health.has_fault,
      activeSensors: onlineCount,
      sensorCount,
      fusedScore: status.fused_score ?? 0,
      confidence: status.confidence ?? 0,
    },
    rgb: {
      label: 'RGB Camera',
      resolution: '1080p',
      fps: 30,
      status: rgbHasFrame ? 'streaming' : 'paused',
      latencyMs: Math.max(0, nowMs - timestampMs),
      frameBase64: visual.rgb_jpeg_b64 ?? null,
      source: 'live',
      stale: !rgbHasFrame,
      lastFrameAtMs: timestampMs,
    },
    thermal: {
      label: 'Thermal Camera',
      resolution: '640x480',
      fps: 30,
      status: thermalHasFrame ? 'streaming' : 'paused',
      latencyMs: Math.max(0, nowMs - timestampMs),
      frameBase64: visual.thermal_jpeg_b64 ?? null,
      source: 'live',
      stale: !thermalHasFrame,
      lastFrameAtMs: timestampMs,
    },
    pointCloud: {
      trackedPoints: pointCloudRaw.length,
      confidence: status.confidence ?? 0,
      lastUpdateMs: Math.max(0, nowMs - timestampMs),
      updateRateHz: 0,
      source: 'live',
      stale: pointCloudRaw.length === 0,
      lastFrameAtMs: timestampMs,
      renderPoints: toRenderPoints(pointCloudRaw),
    },
    presence: {
      detected,
      confidence: presenceConfidence,
      lastTriggerIso: detected ? new Date(timestampMs).toISOString() : '',
      timeline: dashboardSnapshot.presence.timeline,
    },
    alerts: alerts.map((alert, index) => ({
      id: alert.event_id ?? `alert-${index}`,
      level: toAlertLevel(alert.level),
      timestamp: alert.timestamp_utc ? new Date(alert.timestamp_utc).toLocaleTimeString() : '--:--:--',
      message: alert.message ?? 'No message',
    })),
  };
}

function parseWsEvent(input: string): BackendWsEvent | null {
  try {
    const parsed = JSON.parse(input) as BackendWsEvent;
    if (!parsed || typeof parsed.event_type !== 'string') return null;
    return parsed;
  } catch {
    return null;
  }
}

function updateFromWs(current: DashboardSnapshot, event: BackendWsEvent): DashboardSnapshot {
  const next = { ...current };
  if (event.event_type === 'status_update' && event.payload && typeof event.payload === 'object') {
    const payload = event.payload as BackendStatusResponse;
    next.state = (payload.state ?? current.state) as DashboardSnapshot['state'];
    next.health = {
      ...next.health,
      fusedScore: payload.fused_score ?? next.health.fusedScore,
      confidence: payload.confidence ?? next.health.confidence,
      activeSensors: payload.health?.sensor_online_count ?? next.health.activeSensors,
      connected: (payload.health?.sensor_online_count ?? 0) > 0,
      configured: (payload.health?.sensor_online_count ?? 0) > 0,
      streaming: (payload.health?.sensor_online_count ?? 0) > 0,
      healthy: !Boolean(payload.health?.has_fault),
    };
    return next;
  }

  if (event.event_type === 'alert_event' && event.payload && typeof event.payload === 'object') {
    const payload = event.payload as BackendAlert;
    const record = {
      id: payload.event_id ?? `alert-${Date.now()}`,
      level: toAlertLevel(payload.level),
      timestamp: payload.timestamp_utc ? new Date(payload.timestamp_utc).toLocaleTimeString() : '--:--:--',
      message: payload.message ?? 'No message',
    };
    next.alerts = [record, ...next.alerts].slice(0, 100);
    return next;
  }

  if (event.event_type === 'visual_update' && event.payload && typeof event.payload === 'object') {
    const payload = event.payload as BackendVisualLatest;
    const pointCloudRaw = Array.isArray(payload.point_cloud) ? payload.point_cloud : [];
    const detected =
      typeof payload.presence === 'boolean'
        ? payload.presence
        : typeof payload.presence === 'object' && payload.presence !== null
          ? Boolean(payload.presence.detected)
          : current.presence.detected;
    const confidence =
      typeof payload.presence === 'object' && payload.presence !== null && typeof payload.presence.confidence === 'number'
        ? payload.presence.confidence
        : current.presence.confidence;
    const nowMs = Date.now();
    const eventTs = payload.timestamp_ms ?? nowMs;

    next.rgb = {
      ...next.rgb,
      frameBase64: payload.rgb_jpeg_b64 ?? next.rgb.frameBase64,
      status: payload.rgb_jpeg_b64 ? 'streaming' : next.rgb.status,
      source: 'live',
      stale: !payload.rgb_jpeg_b64,
      lastFrameAtMs: eventTs,
      latencyMs: Math.max(0, nowMs - eventTs),
    };
    next.thermal = {
      ...next.thermal,
      frameBase64: payload.thermal_jpeg_b64 ?? next.thermal.frameBase64,
      status: payload.thermal_jpeg_b64 ? 'streaming' : next.thermal.status,
      source: 'live',
      stale: !payload.thermal_jpeg_b64,
      lastFrameAtMs: eventTs,
      latencyMs: Math.max(0, nowMs - eventTs),
    };
    next.pointCloud = {
      ...next.pointCloud,
      trackedPoints: pointCloudRaw.length,
      source: 'live',
      stale: pointCloudRaw.length === 0,
      lastFrameAtMs: eventTs,
      lastUpdateMs: Math.max(0, nowMs - eventTs),
      renderPoints: toRenderPoints(pointCloudRaw),
    };
    next.presence = {
      ...next.presence,
      detected,
      confidence,
      timeline: [...next.presence.timeline.slice(-29), Math.round(confidence * 100)],
      lastTriggerIso: detected ? new Date().toISOString() : next.presence.lastTriggerIso,
    };
    return next;
  }

  if (event.event_type === 'sensor_fault') {
    next.health = { ...next.health, healthy: false };
    next.alerts = [
      {
        id: `fault-${Date.now()}`,
        level: 'fault' as const,
        timestamp: new Date().toLocaleTimeString(),
        message: 'Sensor fault event detected.',
      },
      ...next.alerts,
    ].slice(0, 100);
    return next;
  }

  if (event.event_type === 'control_result' && event.payload && typeof event.payload === 'object') {
    const payload = event.payload as ControlResult;
    const level: AlertLevel = payload.success ? 'info' : 'warning';
    next.alerts = [
      {
        id: `ctrl-${Date.now()}`,
        level,
        timestamp: new Date().toLocaleTimeString(),
        message: `${payload.action ?? 'control'} ${payload.success ? 'ok' : 'failed'}${payload.reason ? ` (${payload.reason})` : ''}`,
      },
      ...next.alerts,
    ].slice(0, 100);
    return next;
  }
  return next;
}

function applyFreshness(snapshot: DashboardSnapshot, staleThresholdMs = 7000): DashboardSnapshot {
  const now = Date.now();
  const rgbStale = now - snapshot.rgb.lastFrameAtMs > staleThresholdMs;
  const thermalStale = now - snapshot.thermal.lastFrameAtMs > staleThresholdMs;
  const pcStale = now - snapshot.pointCloud.lastFrameAtMs > staleThresholdMs;

  return {
    ...snapshot,
    rgb: {
      ...snapshot.rgb,
      stale: snapshot.rgb.source === 'live' ? rgbStale : snapshot.rgb.stale,
      status: snapshot.rgb.source === 'live' && rgbStale ? 'fault' : snapshot.rgb.status,
      latencyMs: Math.max(0, now - snapshot.rgb.lastFrameAtMs),
    },
    thermal: {
      ...snapshot.thermal,
      stale: snapshot.thermal.source === 'live' ? thermalStale : snapshot.thermal.stale,
      status: snapshot.thermal.source === 'live' && thermalStale ? 'fault' : snapshot.thermal.status,
      latencyMs: Math.max(0, now - snapshot.thermal.lastFrameAtMs),
    },
    pointCloud: {
      ...snapshot.pointCloud,
      stale: snapshot.pointCloud.source === 'live' ? pcStale : snapshot.pointCloud.stale,
      lastUpdateMs: Math.max(0, now - snapshot.pointCloud.lastFrameAtMs),
    },
  };
}

function toFallbackSnapshot(reason: string): DashboardSnapshot {
  const now = Date.now();
  return {
    ...dashboardSnapshot,
    rgb: { ...dashboardSnapshot.rgb, source: 'fallback', stale: false, lastFrameAtMs: now },
    thermal: { ...dashboardSnapshot.thermal, source: 'fallback', stale: false, lastFrameAtMs: now },
    pointCloud: { ...dashboardSnapshot.pointCloud, source: 'fallback', stale: false, lastFrameAtMs: now, renderPoints: pointCloudPoints },
    alerts: [
      {
        id: `fallback-${now}`,
        level: 'warning',
        timestamp: new Date(now).toLocaleTimeString(),
        message: `Using fallback data (${reason}).`,
      },
      ...dashboardSnapshot.alerts,
    ],
  };
}

export const dashboardApi = {
  async fetchSnapshot(): Promise<DashboardSnapshot> {
    try {
      const [status, health, alertsResponse, visual] = await Promise.all([
        fetchJson<BackendStatusResponse>(`${API_BASE}/api/status`),
        fetchJson<BackendHealthResponse>(`${API_BASE}/api/health`),
        fetchJson<{ alerts: BackendAlert[] }>(`${API_BASE}/api/alerts/recent?limit=50`),
        fetchJson<BackendVisualLatest>(`${API_BASE}/api/visual/latest`),
      ]);
      return applyFreshness(toDashboardSnapshot(status, health, alertsResponse.alerts ?? [], visual));
    } catch {
      return toFallbackSnapshot('backend unreachable');
    }
  },

  createEventsSocket(): WebSocket {
    return new WebSocket(WS_EVENTS_URL);
  },

  async fetchUiPrefs(): Promise<Partial<UiPreferences> | null> {
    try {
      return await fetchJson<Partial<UiPreferences>>(PREFS_ENDPOINT);
    } catch {
      return null;
    }
  },

  async saveUiPrefs(prefs: UiPreferences): Promise<void> {
    try {
      await postJson(PREFS_ENDPOINT, prefs as unknown as Record<string, unknown>);
    } catch {
      // Best effort only.
    }
  },

  async start(radarId = 'radar_main'): Promise<ControlResult> {
    return postJson<ControlResult>(`${API_BASE}/api/control/reconfig`, {
      radar_id: radarId,
      config_text: 'sensorStart',
    });
  },

  async stop(radarId = 'radar_main'): Promise<ControlResult> {
    return postJson<ControlResult>(`${API_BASE}/api/control/reconfig`, {
      radar_id: radarId,
      config_text: 'sensorStop',
    });
  },

  async reconfigure(radarId = 'radar_main'): Promise<ControlResult> {
    return postJson<ControlResult>(`${API_BASE}/api/control/reconfig`, {
      radar_id: radarId,
      config_text: 'sensorStop\nsensorStart',
    });
  },

  async reset(radarId = 'radar_main'): Promise<ControlResult> {
    return postJson<ControlResult>(`${API_BASE}/api/control/reset-soft`, {
      radar_id: radarId,
    });
  },

  parseWsEvent,
  updateFromWs,
  applyFreshness,
};
