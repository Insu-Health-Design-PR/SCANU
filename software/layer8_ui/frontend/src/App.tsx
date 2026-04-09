import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import {
  fetchHealth,
  fetchRecentAlerts,
  fetchSensorStatus,
  fetchSensorsStatus,
  fetchStatus,
  fetchVisualLatest,
  postKillHolders,
  postReconfig,
  postResetSoft,
  postUsbReset,
} from "./lib/apiClient";
import { WsClient } from "./lib/wsClient";
import { ConnectionBadge } from "./components/ConnectionBadge";
import { ModeSelector } from "./components/ModeSelector";
import { FaultBanner } from "./components/FaultBanner";
import { DashboardPage } from "./pages/DashboardPage";
import { ControlPage } from "./pages/ControlPage";
import { EventsPage } from "./pages/EventsPage";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";
import { appReducer, createInitialState, normalizeStatus } from "./store/appStore";
import type { ConnectionState, ConsoleMode, ControlResult, SensorStatus } from "./types";
import type { SensorAction } from "./components/SensorCards";

function mapWsState(wsState: "connecting" | "connected" | "reconnecting" | "closed"): ConnectionState {
  if (wsState === "connected") return "connected";
  if (wsState === "closed") return "offline";
  return "degraded";
}

export default function App() {
  const [state, dispatch] = useReducer(appReducer, undefined, createInitialState);
  const navigate = useNavigate();
  const location = useLocation();
  const wsRef = useRef<WsClient | null>(null);

  const refreshAll = useCallback(async () => {
    try {
      const [status, health, alerts, sensors, visual] = await Promise.all([
        fetchStatus(),
        fetchHealth(),
        fetchRecentAlerts(100),
        fetchSensorsStatus(),
        fetchVisualLatest(),
      ]);
      dispatch({ type: "UPSERT_STATUS", status: normalizeStatus(status), ts: Date.now() });
      dispatch({ type: "SET_HEALTH", health });
      dispatch({ type: "SET_ALERTS", alerts });
      dispatch({ type: "SET_SENSORS", sensors });
      dispatch({ type: "SET_VISUAL", visual });
    } catch {
      dispatch({ type: "SET_CONNECTION", connection: "degraded" });
    }
  }, []);

  const executeAction = useCallback(
    async (sensor: SensorStatus, action: SensorAction, payload?: { config_path?: string; config_text?: string }) => {
      if (state.mode === "monitor") return;
      if (state.mode === "control" && (action === "kill_holders" || action === "usb_reset")) return;

      let result: ControlResult;
      if (action === "status") {
        const updated = await fetchSensorStatus(sensor.radar_id);
        dispatch({ type: "UPSERT_SENSOR", sensor: updated });
        return;
      }
      if (action === "reconfig") {
        result = await postReconfig({
          radar_id: sensor.radar_id,
          config_path: payload?.config_path,
          config_text: payload?.config_text,
        });
      } else if (action === "reset_soft") {
        result = await postResetSoft({ radar_id: sensor.radar_id });
      } else if (action === "kill_holders") {
        result = await postKillHolders({ radar_id: sensor.radar_id, force: true, manual_confirm: true });
      } else {
        result = await postUsbReset({ radar_id: sensor.radar_id, manual_confirm: true });
      }

      dispatch({ type: "ADD_CONTROL_RESULT", result });
      await refreshAll();
    },
    [refreshAll, state.mode],
  );

  useEffect(() => {
    void refreshAll();
    const timer = window.setInterval(() => {
      void refreshAll();
    }, 10_000);
    return () => window.clearInterval(timer);
  }, [refreshAll]);

  useEffect(() => {
    const ws = new WsClient({
      onState: (wsState) => {
        dispatch({ type: "SET_CONNECTION", connection: mapWsState(wsState) });
      },
      onReconnect: () => {
        void refreshAll();
      },
      onMessage: (event) => {
        const now = Date.now();
        dispatch({ type: "WS_MESSAGE", ts: now });

        if (event.event_type === "status_update") {
          dispatch({ type: "UPSERT_STATUS", status: normalizeStatus(event.payload as any), ts: now });
          return;
        }
        if (event.event_type === "alert_event") {
          dispatch({ type: "ADD_ALERT", alert: event.payload as any });
          return;
        }
        if (event.event_type === "control_result") {
          dispatch({ type: "ADD_CONTROL_RESULT", result: event.payload as any });
          return;
        }
        if (event.event_type === "visual_update") {
          dispatch({ type: "SET_VISUAL", visual: event.payload as any });
          return;
        }
        if (event.event_type === "sensor_fault") {
          dispatch({ type: "SET_SENSOR_FAULT", payload: (event.payload as any) ?? null });
          return;
        }
        if (event.event_type === "heartbeat") {
          dispatch({ type: "HEARTBEAT", ts: now });
        }
      },
    });
    wsRef.current = ws;
    ws.connect();

    return () => {
      ws.close();
    };
  }, [refreshAll]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      const now = Date.now();
      if (state.lastHeartbeatMs == null) return;
      if (now - state.lastHeartbeatMs > 25_000 && state.connection === "connected") {
        dispatch({ type: "SET_CONNECTION", connection: "degraded" });
      }
    }, 3000);

    return () => window.clearInterval(timer);
  }, [state.connection, state.lastHeartbeatMs]);

  useKeyboardShortcuts({
    refresh: () => {
      void refreshAll();
    },
    goDashboard: () => navigate("/dashboard"),
    goControl: () => navigate("/control"),
  });

  const subtitle = useMemo(() => {
    if (location.pathname.includes("control")) return "Control Plane";
    if (location.pathname.includes("events")) return "Event History";
    return "Live Dashboard";
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>SCAN-U Layer 8</h1>
          <p>{subtitle}</p>
        </div>
        <div className="topbar-right">
          <ConnectionBadge state={state.connection} />
          <ModeSelector mode={state.mode} onChange={(mode: ConsoleMode) => dispatch({ type: "SET_MODE", mode })} />
          <button className="btn" onClick={() => void refreshAll()}>
            Refresh
          </button>
        </div>
      </header>

      <nav className="tabs">
        <NavLink to="/dashboard" className={({ isActive }) => (isActive ? "tab active" : "tab")}>
          Dashboard
        </NavLink>
        <NavLink to="/control" className={({ isActive }) => (isActive ? "tab active" : "tab")}>
          Control
        </NavLink>
        <NavLink to="/events" className={({ isActive }) => (isActive ? "tab active" : "tab")}>
          Events
        </NavLink>
      </nav>

      <main>
        <FaultBanner payload={state.lastSensorFault} />
        <Routes>
          <Route
            path="/dashboard"
            element={
              <DashboardPage
                status={state.status}
                health={state.health}
                sensors={state.sensors}
                alerts={state.alerts}
                scoreHistory={state.scoreHistory}
                visual={state.visual}
                mode={state.mode}
                onSensorAction={(sensor, action) => {
                  void executeAction(sensor, action);
                }}
              />
            }
          />
          <Route
            path="/control"
            element={<ControlPage mode={state.mode} sensors={state.sensors} results={state.controlResults} onAction={executeAction} />}
          />
          <Route path="/events" element={<EventsPage alerts={state.alerts} />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}
