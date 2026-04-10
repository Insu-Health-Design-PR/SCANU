import { DashboardShell } from '@/components/layout/DashboardShell';
import { LayoutRenderer } from '@/components/layout/LayoutRenderer';
import { TopBar } from '@/components/layout/TopBar';
import { useDashboardSnapshot } from '@/hooks/useDashboardSnapshot';

export function DashboardPage() {
  useDashboardSnapshot();

  return (
    <DashboardShell>
      <TopBar />
      <LayoutRenderer />
    </DashboardShell>
  );
}
