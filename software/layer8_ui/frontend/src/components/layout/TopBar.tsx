import { ViewLayoutButton } from '@/components/view-layout/ViewLayoutButton';
import { useDashboardStore } from '@/store/dashboardStore';

export function TopBar() {
  const snapshot = useDashboardStore((state) => state.snapshot);
  const modeLabel = snapshot.mode === 'live' ? 'Live' : 'Simulated';
  const healthLabel = snapshot.health.healthy ? 'Healthy' : 'Fault';

  return (
    <header className="mb-6 flex flex-col gap-4 rounded-panel border border-white/10 bg-[linear-gradient(180deg,rgba(12,19,32,0.84),rgba(8,13,23,0.76))] px-5 py-4 shadow-panel backdrop-blur-xl lg:flex-row lg:items-center lg:justify-between">
      <h1 className="text-[2.1rem] font-medium tracking-tight text-white md:text-[2.35rem]">SCAN-U Monitor</h1>

      <div className="flex flex-wrap items-center gap-3">
        <ViewLayoutButton />
        <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-200">
          <span className="inline-flex h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_8px_rgba(34,211,238,0.85)]" />
          <span>{modeLabel}</span>
          <span className="text-slate-500">|</span>
          <span>{healthLabel}</span>
        </div>
      </div>
    </header>
  );
}
