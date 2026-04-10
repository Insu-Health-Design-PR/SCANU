import type { DashboardSnapshot } from '@/types/domain';
import { dashboardSnapshot } from '@/data/mock/dashboardSnapshot';

/**
 * Future backend adapter.
 * Replace the mock return values with FastAPI HTTP or WebSocket integration.
 */
export const dashboardApi = {
  async fetchSnapshot(): Promise<DashboardSnapshot> {
    return Promise.resolve(dashboardSnapshot);
  },
};
