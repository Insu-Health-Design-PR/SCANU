import { DashboardShell } from '@/components/layout/DashboardShell';
import { LayoutRenderer } from '@/components/layout/LayoutRenderer';
import { TopBar } from '@/components/layout/TopBar';
import { useDashboardSnapshot } from '@/hooks/useDashboardSnapshot';

export function DashboardPage() {
  useDashboardSnapshot();

  return (
    <DashboardShell>
      <TopBar />
      <section className="rounded-panel border border-white/10 bg-[radial-gradient(circle_at_20%_0%,rgba(34,211,238,0.08),transparent_30%),linear-gradient(180deg,rgba(12,19,32,0.7),rgba(8,13,23,0.64))] p-4 shadow-panel backdrop-blur-xl md:p-5">
        <LayoutRenderer />
      </section>
    </DashboardShell>
  );
}
