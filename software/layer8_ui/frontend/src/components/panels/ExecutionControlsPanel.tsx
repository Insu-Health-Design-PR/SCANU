import { Play, RotateCcw, Square } from 'lucide-react';
import { PanelCard } from '@/components/shared/PanelCard';
import { StatusChip } from '@/components/shared/StatusChip';

export function ExecutionControlsPanel() {
  return (
    <PanelCard title="Execution Controls" icon={<Play className="h-4 w-4" />}>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <button className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-200">Start</button>
        <button className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">Stop</button>
        <button className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">Reconfigure</button>
        <button className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">Reset</button>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <StatusChip label="Live" tone="cyan" />
        <StatusChip label="Simulated" tone="slate" />
        <StatusChip label="All Sensors" tone="slate" />
      </div>
      <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-3 text-xs text-slate-400">
        TODO: bind these controls to FastAPI commands or websocket control messages.
      </div>
    </PanelCard>
  );
}
