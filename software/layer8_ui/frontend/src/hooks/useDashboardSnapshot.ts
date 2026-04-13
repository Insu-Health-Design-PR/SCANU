import { useEffect } from 'react';
import { useDashboardStore } from '@/store/dashboardStore';
import { dashboardApi } from '@/services/dashboardApi';

/**
 * Bootstraps dashboard data.
 * Later this can attach polling or websocket updates.
 */
export function useDashboardSnapshot() {
  const snapshot = useDashboardStore((state) => state.snapshot);
  const setSnapshot = useDashboardStore((state) => state.setSnapshot);
  const updateSnapshot = useDashboardStore((state) => state.updateSnapshot);

  useEffect(() => {
    let disposed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;

    const loadBootstrap = async () => {
      const next = await dashboardApi.fetchSnapshot();
      if (!disposed) setSnapshot(next);
    };

    const connectSocket = () => {
      socket = dashboardApi.createEventsSocket();

      socket.onmessage = (event) => {
        const parsed = dashboardApi.parseWsEvent(event.data);
        if (!parsed || disposed) return;
        updateSnapshot((current) => dashboardApi.updateFromWs(current, parsed));
      };

      socket.onclose = () => {
        if (disposed) return;
        reconnectTimer = window.setTimeout(connectSocket, 2000);
      };
    };

    void loadBootstrap();
    connectSocket();

    return () => {
      disposed = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      if (socket && socket.readyState === WebSocket.OPEN) socket.close();
    };
  }, [setSnapshot, updateSnapshot]);

  return snapshot;
}
