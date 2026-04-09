import type { AlertPayload, ControlResult, HealthResponse, SensorStatus, StatusPayload, VisualPayload } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function jsonRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} for ${path}`);
  }
  return (await response.json()) as T;
}

export async function fetchStatus(): Promise<StatusPayload> {
  return jsonRequest<StatusPayload>("/api/status");
}

export async function fetchHealth(): Promise<HealthResponse> {
  return jsonRequest<HealthResponse>("/api/health");
}

export async function fetchRecentAlerts(limit = 50): Promise<AlertPayload[]> {
  const data = await jsonRequest<{ alerts: AlertPayload[] }>(`/api/alerts/recent?limit=${limit}`);
  return data.alerts;
}

export async function fetchSensorsStatus(): Promise<SensorStatus[]> {
  const data = await jsonRequest<{ sensors: SensorStatus[] }>("/api/sensors/status");
  return data.sensors;
}

export async function fetchSensorStatus(radarId: string): Promise<SensorStatus> {
  return jsonRequest<SensorStatus>(`/api/sensors/status/${encodeURIComponent(radarId)}`);
}

export async function fetchVisualLatest(): Promise<VisualPayload> {
  return jsonRequest<VisualPayload>("/api/visual/latest");
}

export async function postReconfig(payload: {
  radar_id: string;
  config_path?: string;
  config_text?: string;
}): Promise<ControlResult> {
  return jsonRequest<ControlResult>("/api/control/reconfig", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function postResetSoft(payload: { radar_id: string }): Promise<ControlResult> {
  return jsonRequest<ControlResult>("/api/control/reset-soft", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function postKillHolders(payload: {
  radar_id: string;
  force: boolean;
  manual_confirm: boolean;
}): Promise<ControlResult> {
  return jsonRequest<ControlResult>("/api/control/kill-holders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function postUsbReset(payload: {
  radar_id: string;
  manual_confirm: boolean;
}): Promise<ControlResult> {
  return jsonRequest<ControlResult>("/api/control/usb-reset", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
