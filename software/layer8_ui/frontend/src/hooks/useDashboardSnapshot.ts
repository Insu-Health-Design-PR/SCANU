import { useEffect } from 'react';
import { useDashboardStore } from '@/store/dashboardStore';
import { dashboardApi } from '@/services/dashboardApi';

/**
 * Bootstraps dashboard data and keeps realtime freshness indicators updated.
 */
export function useDashboardSnapshot() {
  const snapshot = useDashboardStore((state) => state.snapshot);
  const setSnapshot = useDashboardStore((state) => state.setSnapshot);
  const updateSnapshot = useDashboardStore((state) => state.updateSnapshot);
  const hydratePrefs = useDashboardStore((state) => state.hydratePrefs);

  useEffect(() => {
    let disposed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let freshnessTimer: number | null = null;

    const loadBootstrap = async () => {
      await hydratePrefs();
      const next = await dashboardApi.fetchSnapshot();
      if (!disposed) setSnapshot(next);
    };

    const connectSocket = () => {
      socket = dashboardApi.createEventsSocket();

      socket.onmessage = (event) => {
        const parsed = dashboardApi.parseWsEvent(event.data);
        if (!parsed || disposed) return;
        updateSnapshot((current) => dashboardApi.applyFreshness(dashboardApi.updateFromWs(current, parsed)));
      };

      socket.onclose = () => {
        if (disposed) return;
        reconnectTimer = window.setTimeout(connectSocket, 2000);
      };
    };

    freshnessTimer = window.setInterval(() => {
      if (disposed) return;
      updateSnapshot((current) => dashboardApi.applyFreshness(current));
    }, 1000);

    void loadBootstrap();
    connectSocket();

    return () => {
      disposed = true;
      if (freshnessTimer !== null) window.clearInterval(freshnessTimer);
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      if (socket && socket.readyState === WebSocket.OPEN) socket.close();
    };
  }, [hydratePrefs, setSnapshot, updateSnapshot]);

  return snapshot;
}
