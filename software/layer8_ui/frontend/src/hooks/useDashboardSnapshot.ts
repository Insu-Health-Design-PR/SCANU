import { useEffect } from 'react';
import { useDashboardStore } from '@/store/dashboardStore';
import { dashboardApi } from '@/services/dashboardApi';

/**
 * Bootstraps dashboard data.
 * Later this can attach polling or websocket updates.
 */
export function useDashboardSnapshot() {
  const snapshot = useDashboardStore((state) => state.snapshot);

  useEffect(() => {
    void dashboardApi.fetchSnapshot();
  }, []);

  return snapshot;
}
