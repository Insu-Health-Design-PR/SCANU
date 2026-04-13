import { Terminal } from 'lucide-react';
import { PanelCard } from '@/components/shared/PanelCard';
import { useDashboardStore } from '@/store/dashboardStore';

export function ConsoleLogPanel() {
  const alerts = useDashboardStore((state) => state.snapshot.alerts);

  return (
    <PanelCard title="Console Log" icon={<Terminal className="h-4 w-4" />}>
      <div className="max-h-[210px] space-y-2 overflow-auto rounded-2xl border border-white/10 bg-slate-950 p-3">
        {alerts.map((entry) => (
          <div key={entry.id} className="grid grid-cols-[56px_72px_1fr] gap-3 rounded-xl border border-white/5 bg-white/[0.03] p-3 text-xs text-slate-300">
            <span className={entry.level === 'fault' ? 'text-rose-300' : entry.level === 'warning' ? 'text-amber-300' : 'text-cyan-300'}>
              {entry.level.toUpperCase()}
            </span>
            <span className="text-slate-500">{entry.timestamp}</span>
            <span>{entry.message}</span>
          </div>
        ))}
      </div>
    </PanelCard>
  );
}
