import { LayoutGrid, ShieldCheck } from 'lucide-react';
import { StatusChip } from '@/components/shared/StatusChip';
import { ViewLayoutButton } from '@/components/view-layout/ViewLayoutButton';
import { useDashboardStore } from '@/store/dashboardStore';

export function TopBar() {
  const snapshot = useDashboardStore((state) => state.snapshot);
  const appliedLayout = useDashboardStore((state) => state.appliedLayout);

  return (
    <header className="mb-6 flex flex-col gap-4 rounded-panel border border-white/10 bg-surface-800/70 px-6 py-5 shadow-panel backdrop-blur-xl lg:flex-row lg:items-center lg:justify-between">
      <div>
        <div className="text-sm uppercase tracking-[0.32em] text-slate-500">Layer 8 Dashboard</div>
        <h1 className="mt-2 text-4xl font-medium tracking-tight text-white">SCAN-U Monitor</h1>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <StatusChip label={snapshot.mode === 'live' ? 'Live' : 'Simulated'} tone="cyan" />
        <StatusChip label={snapshot.health.healthy ? 'Healthy' : 'Fault'} tone={snapshot.health.healthy ? 'green' : 'red'} />
        <StatusChip label={snapshot.state} tone={snapshot.state === 'SCANNING' ? 'amber' : 'slate'} />
        <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
          <LayoutGrid className="h-3.5 w-3.5" />
          {appliedLayout}
        </span>
        <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-xs text-emerald-200">
          <ShieldCheck className="h-3.5 w-3.5" />
          Connected
        </span>
        <ViewLayoutButton />
      </div>
    </header>
  );
}
