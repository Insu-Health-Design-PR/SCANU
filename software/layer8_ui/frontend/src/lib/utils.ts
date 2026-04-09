import type { AlertLevel, SystemState } from "../types";

export const STATE_COLORS: Record<SystemState, string> = {
  UNKNOWN: "#6b7280",
  IDLE: "#3b82f6",
  TRIGGERED: "#f59e0b",
  SCANNING: "#eab308",
  ANOMALY_DETECTED: "#ef4444",
  FAULT: "#dc2626",
};

export const ALERT_COLORS: Record<AlertLevel, string> = {
  INFO: "#22c55e",
  WARNING: "#f59e0b",
  ALERT: "#f97316",
  FAULT: "#ef4444",
};

export function clamp(value: number, min = 0, max = 1): number {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

export function formatTimeIso(value?: string | null): string {
  if (!value) return "-";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  return dt.toLocaleString();
}

export function formatMs(value?: number | null): string {
  if (value == null) return "-";
  return `${Math.round(value)} ms`;
}
